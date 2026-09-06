using System.Text.Json;
using Xunit;

namespace RoNCT.Tests.Localization;

public sealed class LocalizationFilesTests
{
    private static string LocalizationDirectory =>
        Path.Combine(
            Path.GetFullPath(Path.Combine(
                AppContext.BaseDirectory, "..", "..", "..", "..", "..")),
            "src", "RoNCT.App", "Assets", "Localization");

    [Fact]
    public void EnglishAndChinese_HaveIdenticalKeySets()
    {
        var english = Load("en");
        var chinese = Load("zh");

        Assert.True(
            english.Keys.ToHashSet().SetEquals(chinese.Keys),
            $"Key mismatch between en.json and zh.json. Missing in zh: " +
            $"{string.Join(", ", english.Keys.Except(chinese.Keys))}; " +
            $"missing in en: {string.Join(", ", chinese.Keys.Except(english.Keys))}");
    }

    [Fact]
    public void RequiredKeys_ExistAndHaveNonEmptyValues()
    {
        string[] required =
        {
            "App.Title", "Nav.Test", "Nav.Nexus", "Nav.Backup",
            "Nav.Quarantine", "Nav.Advanced", "Footer.Theme",
            "Footer.Language", "Theme.System", "Theme.Light", "Theme.Dark",
        };

        foreach (var language in new[] { "en", "zh" })
        {
            var table = Load(language);
            foreach (var key in required)
            {
                Assert.True(
                    table.TryGetValue(key, out var value) && !string.IsNullOrWhiteSpace(value),
                    $"{language}.json is missing a non-empty value for '{key}'.");
            }
        }
    }

    private static Dictionary<string, string> Load(string language)
    {
        var path = Path.Combine(LocalizationDirectory, $"{language}.json");
        Assert.True(File.Exists(path), $"Missing localization file: {path}");
        return JsonSerializer.Deserialize<Dictionary<string, string>>(
            File.ReadAllText(path))!;
    }
}
