using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace RoNCT.App.Services;

public sealed class NexusModInfo
{
    public string? Name { get; set; }
    public long? ModId { get; set; }
    public string? ModUrl { get; set; }
    public string? FileName { get; set; }
    public string? Version { get; set; }
    public string? Author { get; set; }
}

public sealed class NexusDependency
{
    public long? ModId { get; set; }
    public string? Name { get; set; }
}

public static class NexusClient
{
    private const string RestBaseUri = "https://api.nexusmods.com/v1";
    private const string GraphQlUri = "https://api.nexusmods.com/v2/graphql";
    private const string GameDomain = "readyornot";

    private static readonly SemaphoreSlim ThrottleGate = new(1, 1);
    private static DateTime _lastRequestUtc = DateTime.MinValue;

    private static readonly HashSet<string> CommonTokens = new(
        new[]
        {
            "addon", "addons", "and", "asset", "assets", "blueprint", "blueprints",
            "bp", "content", "contents", "dlc", "fix", "fixed", "fixes", "main",
            "mod", "mods", "new", "no", "pack", "packs", "pak", "pakchunk",
            "plus", "texture", "textures", "the", "ui", "uis", "update", "updated",
        },
        StringComparer.OrdinalIgnoreCase);

    private static readonly Dictionary<string, string[]> TermVariants = new(
        StringComparer.OrdinalIgnoreCase)
    {
        ["fastrelod"] = new[] { "fast", "reload" },
        ["relod"] = new[] { "reload" },
        ["relods"] = new[] { "reload" },
        ["shutgun"] = new[] { "shotgun" },
        ["shutguns"] = new[] { "shotguns" },
        ["shotgunreload"] = new[] { "shotgun", "reload" },
    };

    public static string Md5(string filePath)
    {
        using var stream = File.OpenRead(filePath);
        return Convert.ToHexString(MD5.HashData(stream)).ToLowerInvariant();
    }

    /// <summary>
    /// Exact Nexus file lookup by MD5. Returns an empty list when Nexus has no
    /// match (HTTP 404 is the API's "hash unknown" answer).
    /// </summary>
    public static async Task<IReadOnlyList<NexusModInfo>> SearchMd5Async(
        string apiKey,
        string md5,
        CancellationToken cancellationToken = default)
    {
        var url = $"{RestBaseUri}/games/{GameDomain}/mods/md5_search/{md5}.json";
        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        var json = await SendAsync(apiKey, request, cancellationToken);
        if (json is null)
        {
            return Array.Empty<NexusModInfo>();
        }
        return ParseMd5Matches(json);
    }

    public static async Task<NexusModInfo?> GetModByMd5Async(
        string apiKey,
        string md5,
        CancellationToken cancellationToken = default)
    {
        var matches = await SearchMd5Async(apiKey, md5, cancellationToken);
        return matches.FirstOrDefault();
    }

    /// <summary>
    /// Nexus GraphQL fuzzy search by one keyword. It works without an exact MD5
    /// match, which is how older RoNCT builds identified local paks.
    /// </summary>
    public static async Task<IReadOnlyList<NexusModInfo>> SearchModsAsync(
        string apiKey,
        string term,
        int limit = 8,
        CancellationToken cancellationToken = default)
    {
        const string query = """
            query RoNCTSearch($game: String!, $term: String!, $count: Int!) {
              mods(
                filter: {
                  gameDomainName: [{ value: $game, op: EQUALS }]
                  nameStemmed: [{ value: $term, op: MATCHES }]
                }
                count: $count
              ) {
                nodes {
                  modId
                  name
                  author
                }
              }
            }
            """;
        var body = new
        {
            query,
            variables = new { game = GameDomain, term, count = limit },
        };
        using var request = new HttpRequestMessage(HttpMethod.Post, GraphQlUri);
        request.Content = new StringContent(
            JsonSerializer.Serialize(body), Encoding.UTF8, "application/json");
        request.Headers.TryAddWithoutValidation("Origin", "https://www.nexusmods.com");
        request.Headers.TryAddWithoutValidation("Referer", "https://www.nexusmods.com/");

        var json = await SendAsync(apiKey, request, cancellationToken);
        if (json is null)
        {
            return Array.Empty<NexusModInfo>();
        }

        var result = new List<NexusModInfo>();
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        if (!root.TryGetProperty("data", out var data) ||
            !data.TryGetProperty("mods", out var mods) ||
            !mods.TryGetProperty("nodes", out var nodes))
        {
            return result;
        }

        foreach (var node in nodes.EnumerateArray())
        {
            var modId = GetLong(node, "modId");
            if (modId is null)
            {
                continue;
            }
            result.Add(new NexusModInfo
            {
                ModId = modId,
                Name = GetString(node, "name"),
                Author = GetString(node, "author"),
                ModUrl = $"https://www.nexusmods.com/{GameDomain}/mods/{modId}",
            });
        }
        return result;
    }

    /// <summary>
    /// File-name based candidate search used when the MD5 lookup has no result:
    /// turns "pakchunk99-Fastrelod_shutgun_P.pak" into search keywords and ranks
    /// the Nexus matches.
    /// </summary>
    public static async Task<IReadOnlyList<NexusModInfo>> SearchCandidatesAsync(
        string apiKey,
        string pakFileName,
        CancellationToken cancellationToken = default)
    {
        var rawTerms = QueryTerms(pakFileName);
        var searchTerms = ExpandTerms(rawTerms);
        if (searchTerms.Count == 0)
        {
            return Array.Empty<NexusModInfo>();
        }

        var combined = new Dictionary<long, CandidateEntry>();
        var order = 0;
        foreach (var term in searchTerms.Take(4))
        {
            var matches = await SearchModsAsync(
                apiKey, term, limit: 8, cancellationToken);
            foreach (var match in matches)
            {
                if (match.ModId is null)
                {
                    continue;
                }
                if (!combined.TryGetValue(match.ModId.Value, out var entry))
                {
                    combined[match.ModId.Value] = entry = new CandidateEntry
                    {
                        Info = match,
                        Order = order++,
                    };
                }
                entry.Matched++;
            }
        }

        return combined.Values
            .OrderByDescending(entry => entry.Matched * 4 + NameTokenHits(
                entry.Info.Name, rawTerms))
            .ThenBy(entry => entry.Order)
            .Take(10)
            .Select(entry => entry.Info)
            .ToArray();
    }

    public static async Task<IReadOnlyList<NexusDependency>> GetDependenciesAsync(
        string apiKey,
        long modId,
        CancellationToken cancellationToken = default)
    {
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            $"{RestBaseUri}/games/{GameDomain}/mods/{modId}/dependencies.json");
        var json = await SendAsync(apiKey, request, cancellationToken);
        if (json is null)
        {
            return Array.Empty<NexusDependency>();
        }

        using var doc = JsonDocument.Parse(json);
        if (!doc.RootElement.TryGetProperty("dependencies", out var array))
        {
            return Array.Empty<NexusDependency>();
        }

        var result = new List<NexusDependency>();
        foreach (var item in array.EnumerateArray())
        {
            result.Add(new NexusDependency
            {
                ModId = GetLong(item, "mod_id"),
                Name = GetString(item, "name"),
            });
        }
        return result;
    }

    private static async Task<string?> SendAsync(
        string apiKey,
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        await ThrottleAsync(cancellationToken);
        using var client = new HttpClient();
        client.DefaultRequestHeaders.Add("apikey", apiKey);
        client.DefaultRequestHeaders.Accept.Add(
            new MediaTypeWithQualityHeaderValue("application/json"));
        client.DefaultRequestHeaders.UserAgent.ParseAdd(
            "RoNCT/1.0 (Ready or Not mod compatibility tester)");

        using var response = await client.SendAsync(request, cancellationToken);
        if ((int)response.StatusCode == 404)
        {
            return null;
        }
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(
                $"Nexus API returned {(int)response.StatusCode} for {request.RequestUri}");
        }
        return await response.Content.ReadAsStringAsync(cancellationToken);
    }

    private static async Task ThrottleAsync(CancellationToken cancellationToken)
    {
        await ThrottleGate.WaitAsync(cancellationToken);
        try
        {
            var elapsed = DateTime.UtcNow - _lastRequestUtc;
            if (elapsed < TimeSpan.FromMilliseconds(1100))
            {
                await Task.Delay(
                    TimeSpan.FromMilliseconds(1100) - elapsed,
                    cancellationToken);
            }
            _lastRequestUtc = DateTime.UtcNow;
        }
        finally
        {
            ThrottleGate.Release();
        }
    }

    private static IReadOnlyList<NexusModInfo> ParseMd5Matches(string json)
    {
        using var doc = JsonDocument.Parse(json);
        return EnumerateMatchElements(doc.RootElement)
            .Select(ParseMatchElement)
            .Where(item => item is not null)
            .Cast<NexusModInfo>()
            .ToArray();
    }

    private static IEnumerable<JsonElement> EnumerateMatchElements(JsonElement root)
    {
        if (root.ValueKind == JsonValueKind.Array)
        {
            return root.EnumerateArray().ToArray();
        }

        foreach (var property in new[] { "data", "mods", "results", "matches" })
        {
            if (root.TryGetProperty(property, out var value) &&
                value.ValueKind == JsonValueKind.Array)
            {
                return value.EnumerateArray().ToArray();
            }
        }
        return Array.Empty<JsonElement>();
    }

    private static NexusModInfo? ParseMatchElement(JsonElement item)
    {
        if (item.ValueKind != JsonValueKind.Object)
        {
            return null;
        }
        var mod = item.TryGetProperty("mod", out var modElement) &&
                  modElement.ValueKind == JsonValueKind.Object
            ? modElement
            : item;
        var file = item.TryGetProperty("file", out var fileElement) &&
                   fileElement.ValueKind == JsonValueKind.Object
            ? fileElement
            : mod;
        var modId = GetLong(mod, "mod_id") ?? GetLong(mod, "id");
        if (modId is null)
        {
            return null;
        }
        return new NexusModInfo
        {
            ModId = modId,
            Name = GetString(mod, "name"),
            FileName = GetString(file, "name") ?? GetString(mod, "file_name"),
            Version = GetString(file, "version") ?? GetString(mod, "version"),
            ModUrl = $"https://www.nexusmods.com/{GameDomain}/mods/{modId}",
        };
    }

    private static List<string> QueryTerms(string pakFileName)
    {
        var stem = Path.GetFileNameWithoutExtension(pakFileName);
        stem = Regex.Replace(stem, "^pakchunk[0-9]+[-_]*", string.Empty, RegexOptions.IgnoreCase);
        stem = Regex.Replace(stem, "[-_]*[pP]$", string.Empty);
        stem = CamelBreak.Replace(stem, " ");
        var tokens = Regex.Split(stem, @"[\s_.\-+()\[\]{}]+");
        var terms = new List<string>();
        foreach (var token in tokens)
        {
            var low = token.Trim().Trim('_').ToLowerInvariant();
            if (string.IsNullOrEmpty(low) ||
                CommonTokens.Contains(low) ||
                low.All(char.IsDigit) ||
                low.Length < 3)
            {
                continue;
            }
            if (!terms.Contains(low))
            {
                terms.Add(low);
            }
        }
        return terms;
    }

    private static List<string> ExpandTerms(List<string> rawTerms)
    {
        var terms = new List<string>();
        foreach (var raw in rawTerms.Take(3))
        {
            if (TermVariants.TryGetValue(raw, out var variants))
            {
                foreach (var variant in variants)
                {
                    if (!terms.Contains(variant))
                    {
                        terms.Add(variant);
                    }
                }
            }
            else if (!terms.Contains(raw))
            {
                terms.Add(raw);
            }
            if (terms.Count >= 4)
            {
                break;
            }
        }
        return terms;
    }

    private static int NameTokenHits(string? modName, List<string> rawTerms)
    {
        if (string.IsNullOrWhiteSpace(modName) || rawTerms.Count == 0)
        {
            return 0;
        }
        var words = new HashSet<string>(
            Regex.Split(modName.ToLowerInvariant(), @"[^a-z0-9]+"),
            StringComparer.Ordinal);
        return rawTerms.Count(words.Contains);
    }

    private static readonly Regex CamelBreak = new(
        @"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
        RegexOptions.Compiled);

    private static string? GetString(JsonElement element, string property)
        => element.TryGetProperty(property, out var value) ? value.GetString() : null;

    private static long? GetLong(JsonElement element, string property)
        => element.TryGetProperty(property, out var value) &&
           value.ValueKind == JsonValueKind.Number
            ? value.GetInt64()
            : null;

    private sealed class CandidateEntry
    {
        public NexusModInfo Info { get; init; } = null!;
        public int Order { get; init; }
        public int Matched { get; set; }
    }
}
