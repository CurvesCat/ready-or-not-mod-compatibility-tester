using RoNCT.Core.Deployment;
using Xunit;

namespace RoNCT.Tests.Deployment;

public sealed class ModFolderOperatorTests : IDisposable
{
    private readonly string _root = Path.Combine(
        Path.GetTempPath(), "ronct-isolation-tests-" + Guid.NewGuid().ToString("N"));
    private readonly string _modDir;
    private readonly string _sessionRoot;

    public ModFolderOperatorTests()
    {
        _modDir = Path.Combine(_root, "mods");
        _sessionRoot = Path.Combine(_root, "session");
        Directory.CreateDirectory(_modDir);
    }

    public void Dispose()
    {
        try { Directory.Delete(_root, recursive: true); }
        catch { /* best effort */ }
    }

    [Fact]
    public void ParkOthers_MovesOnlyUnwantedMods()
    {
        File.WriteAllText(Path.Combine(_modDir, "a.pak"), "a");
        File.WriteAllText(Path.Combine(_modDir, "b.pak"), "b");
        var op = new ModFolderOperator(_modDir, _sessionRoot);

        var parked = op.ParkOthers(new[] { "a.pak" });

        Assert.Contains("b.pak", parked);
        Assert.True(File.Exists(Path.Combine(_modDir, "a.pak")));
        Assert.False(File.Exists(Path.Combine(_modDir, "b.pak")));
        Assert.True(File.Exists(Path.Combine(_sessionRoot, "b.pak")));
    }

    [Fact]
    public void RestoreAll_BringsParkedModsBack()
    {
        File.WriteAllText(Path.Combine(_modDir, "a.pak"), "a");
        File.WriteAllText(Path.Combine(_modDir, "b.pak"), "b");
        var op = new ModFolderOperator(_modDir, _sessionRoot);
        op.ParkOthers(new[] { "a.pak" });

        var restored = op.RestoreAll();

        Assert.Contains("b.pak", restored);
        Assert.True(File.Exists(Path.Combine(_modDir, "b.pak")));
        Assert.Equal(0, Directory.EnumerateFiles(_sessionRoot).Count());
    }
}
