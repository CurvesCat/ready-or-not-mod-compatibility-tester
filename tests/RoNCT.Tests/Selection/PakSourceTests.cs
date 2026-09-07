using Xunit;
using RoNCT.Core.Selection;

namespace RoNCT.Tests.Selection;

public sealed class PakSourceTests : IDisposable
{
    private readonly string _dir = Path.Combine(
        Path.GetTempPath(), "ronct-paksource-tests-" + Guid.NewGuid().ToString("N"));

    public PakSourceTests() => Directory.CreateDirectory(_dir);

    public void Dispose()
    {
        try { Directory.Delete(_dir, recursive: true); }
        catch { /* best effort cleanup */ }
    }

    [Fact]
    public void FromFolder_ReturnsOnlyPakFilesSorted()
    {
        File.WriteAllText(Path.Combine(_dir, "b.pak"), string.Empty);
        File.WriteAllText(Path.Combine(_dir, "a.pak"), string.Empty);
        File.WriteAllText(Path.Combine(_dir, "notes.txt"), string.Empty);

        var items = PakSource.FromFolder(_dir);

        Assert.Equal(2, items.Count);
        Assert.Equal("a.pak", items[0].FileName);
        Assert.Equal("b.pak", items[1].FileName);
    }

    [Fact]
    public void FromFiles_KeepsExplicitOrderAndDropsMissingFiles()
    {
        var first = Path.Combine(_dir, "first.pak");
        var second = Path.Combine(_dir, "second.pak");
        File.WriteAllText(first, string.Empty);
        File.WriteAllText(second, string.Empty);

        var items = PakSource.FromFiles(new[] { second, first, Path.Combine(_dir, "missing.pak") });

        Assert.Equal(2, items.Count);
        Assert.Equal("second.pak", items[0].FileName);
        Assert.Equal("first.pak", items[1].FileName);
    }

    [Fact]
    public void IsModPak_RejectsBaseGamePack_AndAcceptsMods()
    {
        Assert.False(PakSource.IsModPak("pakchunk0-Windows.pak"));
        Assert.False(PakSource.IsModPak("pakchunk24-Windows.pak"));
        Assert.False(PakSource.IsModPak("pakchunk0-Windows.sig"));
        Assert.False(PakSource.IsModPak("pakchunk24-Windows.ucas"));
        Assert.True(PakSource.IsModPak("pakchunk99-Mods_BGroupV2_Main_P.pak"));
        Assert.True(PakSource.IsModPak("pakchunk9999-Mods_wound_P.pak"));
    }

    [Fact]
    public void FromGamePaksFolder_ReturnsOnlyModsIncludingSubfolders()
    {
        File.WriteAllText(Path.Combine(_dir, "pakchunk0-Windows.pak"), string.Empty);
        File.WriteAllText(Path.Combine(_dir, "pakchunk24-Windows.pak"), string.Empty);
        File.WriteAllText(Path.Combine(_dir, "pakchunk99-Mods_MyMod_P.pak"), string.Empty);
        var modIo = Path.Combine(_dir, "mod.io");
        Directory.CreateDirectory(modIo);
        File.WriteAllText(Path.Combine(modIo, "pakchunk99-Mods_FromModIo_P.pak"), string.Empty);

        var mods = PakSource.FromGamePaksFolder(_dir);

        Assert.Equal(2, mods.Count);
        Assert.Contains(mods, mod => mod.FileName == "pakchunk99-Mods_MyMod_P.pak");
        Assert.Contains(mods, mod => mod.FileName == "pakchunk99-Mods_FromModIo_P.pak");
        Assert.DoesNotContain(mods, mod => mod.FileName == "pakchunk0-Windows.pak");
    }
}
