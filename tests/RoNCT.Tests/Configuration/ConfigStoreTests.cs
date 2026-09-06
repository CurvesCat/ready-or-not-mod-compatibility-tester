using Xunit;
using RoNCT.Core.Configuration;

namespace RoNCT.Tests.Configuration;

public sealed class ConfigStoreTests : IDisposable
{
    private readonly string _dir = Path.Combine(
        Path.GetTempPath(), "ronct-config-tests-" + Guid.NewGuid().ToString("N"));

    public ConfigStoreTests() => Directory.CreateDirectory(_dir);

    public void Dispose()
    {
        try { Directory.Delete(_dir, recursive: true); }
        catch { /* best effort cleanup */ }
    }

    [Fact]
    public void Load_WhenFileMissing_ReturnsDefaults()
    {
        var config = ConfigStore.Load(_dir);
        Assert.Equal("en", config.Language);
        Assert.Equal("system", config.ThemeMode);
        Assert.Empty(config.SelectedPakFiles);
    }

    [Fact]
    public void Load_WhenFileCorrupt_ReturnsDefaultsWithoutThrowing()
    {
        File.WriteAllText(Path.Combine(_dir, "config.json"), "{ not json");
        var config = ConfigStore.Load(_dir);
        Assert.Equal("en", config.Language);
    }

    [Fact]
    public void SaveAndLoad_RoundTripsValues()
    {
        var original = new AppConfig
        {
            Language = "zh",
            ThemeMode = "dark",
            NexusApiKey = "test-key",
            ModFolder = @"C:\mods",
            StableSeconds = 41,
        };

        ConfigStore.Save(original, _dir);

        var loaded = ConfigStore.Load(_dir);
        Assert.Equal("zh", loaded.Language);
        Assert.Equal("dark", loaded.ThemeMode);
        Assert.Equal("test-key", loaded.NexusApiKey);
        Assert.Equal(@"C:\mods", loaded.ModFolder);
        Assert.Equal(41, loaded.StableSeconds);
    }
}
