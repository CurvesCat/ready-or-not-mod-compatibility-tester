using System.Text.Json;

namespace RoNCT.Core.Configuration;

public static class ConfigStore
{
    public const string FileName = "config.json";

    public static string ConfigPath(string baseDir) =>
        Path.Combine(baseDir, FileName);

    public static AppConfig Load(string baseDir)
    {
        var path = ConfigPath(baseDir);
        if (!File.Exists(path))
        {
            return new AppConfig();
        }

        try
        {
            return JsonSerializer.Deserialize<AppConfig>(
                File.ReadAllText(path)) ?? new AppConfig();
        }
        catch (JsonException)
        {
            return new AppConfig();
        }
    }

    public static void Save(AppConfig config, string baseDir)
    {
        Directory.CreateDirectory(baseDir);
        var json = JsonSerializer.Serialize(
            config, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(ConfigPath(baseDir), json);
    }
}
