using System.Text.Json;

namespace RoNCT.App.Services;

/// <summary>
/// Loads UI strings from the bundled en.json / zh.json files and switches
/// language at runtime without restarting the app.
/// </summary>
public static class Localizer
{
    public const string English = "en";
    public const string Chinese = "zh";

    public static string CurrentLanguage { get; private set; } = English;

    private static Dictionary<string, string>? _english;
    private static Dictionary<string, string>? _chinese;

    public static event EventHandler? LanguageChanged;

    public static string T(string key)
    {
        EnsureLoaded();
        var table = CurrentLanguage == Chinese ? _chinese! : _english!;
        if (table.TryGetValue(key, out var value))
        {
            return value;
        }

        return _english!.TryGetValue(key, out var fallback)
            ? fallback
            : $"?{key}";
    }

    public static void SetLanguage(string language)
    {
        EnsureLoaded();
        var normalized = language == Chinese ? Chinese : English;
        if (CurrentLanguage == normalized)
        {
            return;
        }

        CurrentLanguage = normalized;
        LanguageChanged?.Invoke(null, EventArgs.Empty);
    }

    private static void EnsureLoaded()
    {
        if (_english is not null)
        {
            return;
        }

        _english = Load(English);
        _chinese = Load(Chinese);
    }

    private static Dictionary<string, string> Load(string language)
    {
        var path = Path.Combine(
            AppContext.BaseDirectory, "Assets", "Localization", $"{language}.json");
        if (!File.Exists(path))
        {
            return new Dictionary<string, string>();
        }

        try
        {
            return JsonSerializer.Deserialize<Dictionary<string, string>>(
                File.ReadAllText(path)) ?? new Dictionary<string, string>();
        }
        catch (JsonException)
        {
            return new Dictionary<string, string>();
        }
    }
}
