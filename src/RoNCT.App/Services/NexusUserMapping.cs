using System.Text.Json;

namespace RoNCT.App.Services;

/// <summary>
/// Persists the user's confirm/ignore choices for each pak fingerprint next to
/// the executable (cache/nexus_known_mods.json), like the original Python tool.
/// </summary>
public sealed class NexusMappingRecord
{
    public string Choice { get; set; } = string.Empty;
    public long? ModId { get; set; }
    public string ModName { get; set; } = string.Empty;
    public string ModUrl { get; set; } = string.Empty;
    public string PakName { get; set; } = string.Empty;
    public string Author { get; set; } = string.Empty;
    public string UpdatedAt { get; set; } = string.Empty;
}

public static class NexusUserMapping
{
    public const string Confirmed = "confirmed";
    public const string Ignored = "ignored";

    private static readonly object Gate = new();

    public static string MappingFile =>
        Path.Combine(AppSettings.DataDirectory, "cache", "nexus_known_mods.json");

    public static Dictionary<string, NexusMappingRecord> Load()
    {
        lock (Gate)
        {
            try
            {
                if (!File.Exists(MappingFile))
                {
                    return new Dictionary<string, NexusMappingRecord>(
                        StringComparer.OrdinalIgnoreCase);
                }

                using var doc = JsonDocument.Parse(File.ReadAllText(MappingFile));
                var root = doc.RootElement;
                if (!root.TryGetProperty("entries", out var entries))
                {
                    return new Dictionary<string, NexusMappingRecord>(
                        StringComparer.OrdinalIgnoreCase);
                }

                var result = new Dictionary<string, NexusMappingRecord>(
                    StringComparer.OrdinalIgnoreCase);
                foreach (var property in entries.EnumerateObject())
                {
                    var record = JsonSerializer.Deserialize<NexusMappingRecord>(
                        property.Value.GetRawText());
                    if (record is not null)
                    {
                        result[property.Name] = record;
                    }
                }
                return result;
            }
            catch (Exception exc)
            {
                AppLog.Error("NexusUserMapping load failed: " + exc.Message);
                return new Dictionary<string, NexusMappingRecord>(
                    StringComparer.OrdinalIgnoreCase);
            }
        }
    }

    public static void Confirm(
        string md5,
        long? modId,
        string modName,
        string modUrl,
        string pakName,
        string author)
    {
        Save(md5, new NexusMappingRecord
        {
            Choice = Confirmed,
            ModId = modId,
            ModName = modName,
            ModUrl = modUrl,
            PakName = pakName,
            Author = author,
            UpdatedAt = DateTime.Now.ToString("s"),
        });
    }

    public static void Ignore(string md5, string pakName)
    {
        Save(md5, new NexusMappingRecord
        {
            Choice = Ignored,
            PakName = pakName,
            UpdatedAt = DateTime.Now.ToString("s"),
        });
    }

    private static void Save(string md5, NexusMappingRecord record)
    {
        lock (Gate)
        {
            try
            {
                var entries = Load();
                entries[(md5 ?? string.Empty).Trim().ToLowerInvariant()] = record;
                var payload = JsonSerializer.Serialize(
                    new { schema = 1, entries },
                    new JsonSerializerOptions { WriteIndented = true });
                var path = MappingFile;
                Directory.CreateDirectory(Path.GetDirectoryName(path)!);
                File.WriteAllText(path, payload);
            }
            catch (Exception exc)
            {
                AppLog.Error("NexusUserMapping save failed: " + exc.Message);
            }
        }
    }
}
