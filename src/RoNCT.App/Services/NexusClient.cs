using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;

namespace RoNCT.App.Services;

public sealed class NexusModInfo
{
    public string? Name { get; set; }
    public long? ModId { get; set; }
    public string? ModUrl { get; set; }
}

public sealed class NexusDependency
{
    public long? ModId { get; set; }
    public string? Name { get; set; }
}

public static class NexusClient
{
    private const string BaseUri = "https://api.nexusmods.com/v1";
    private const string GameDomain = "readyornot";

    public static async Task<NexusModInfo?> GetModByMd5Async(
        string apiKey, string md5, CancellationToken cancellationToken = default)
    {
        using var client = CreateClient(apiKey);
        var response = await client.GetAsync(
            $"{BaseUri}/games/{GameDomain}/mods/md5_search/{md5}",
            cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            return null;
        }
        var json = await response.Content.ReadAsStringAsync(cancellationToken);
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        return new NexusModInfo
        {
            Name = GetString(root, "name"),
            ModId = GetLong(root, "mod_id"),
            ModUrl = root.TryGetProperty("mod_id", out var id)
                ? $"https://www.nexusmods.com/{GameDomain}/mods/{id}"
                : null,
        };
    }

    public static async Task<IReadOnlyList<NexusDependency>> GetDependenciesAsync(
        string apiKey, long modId, CancellationToken cancellationToken = default)
    {
        using var client = CreateClient(apiKey);
        var response = await client.GetAsync(
            $"{BaseUri}/games/{GameDomain}/mods/{modId}/dependencies",
            cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            return Array.Empty<NexusDependency>();
        }
        var json = await response.Content.ReadAsStringAsync(cancellationToken);
        using var doc = JsonDocument.Parse(json);
        var array = doc.RootElement.GetProperty("dependencies");
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

    public static string Md5(string filePath)
    {
        using var stream = File.OpenRead(filePath);
        return Convert.ToHexString(MD5.HashData(stream)).ToLowerInvariant();
    }

    private static HttpClient CreateClient(string apiKey)
    {
        var client = new HttpClient();
        client.DefaultRequestHeaders.Add("apikey", apiKey);
        client.DefaultRequestHeaders.Accept.Add(
            new MediaTypeWithQualityHeaderValue("application/json"));
        client.DefaultRequestHeaders.UserAgent.ParseAdd("RoNCT/1.0");
        return client;
    }

    private static string? GetString(JsonElement element, string property)
    {
        return element.TryGetProperty(property, out var value) ? value.GetString() : null;
    }

    private static long? GetLong(JsonElement element, string property)
    {
        return element.TryGetProperty(property, out var value) && value.ValueKind == JsonValueKind.Number
            ? value.GetInt64()
            : null;
    }
}
