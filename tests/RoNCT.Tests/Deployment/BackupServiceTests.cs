using System.Text.Json;
using RoNCT.Core.Deployment;
using Xunit;

namespace RoNCT.Tests.Deployment;

public sealed class BackupServiceTests : IDisposable
{
    private readonly string _root = Path.Combine(
        Path.GetTempPath(), "ronct-backup-tests-" + Guid.NewGuid().ToString("N"));

    public BackupServiceTests() => Directory.CreateDirectory(_root);

    public void Dispose()
    {
        try { Directory.Delete(_root, recursive: true); }
        catch { /* best effort */ }
    }

    [Fact]
    public void SnapshotAndVerify_DetectAddedMissingAndSizeChanges()
    {
        var modDir = Path.Combine(_root, "mods");
        Directory.CreateDirectory(modDir);
        File.WriteAllText(Path.Combine(modDir, "a.pak"), "123");
        var before = BackupService.SnapshotModDir(modDir);

        File.WriteAllText(Path.Combine(modDir, "b.pak"), "x");
        File.AppendAllText(Path.Combine(modDir, "a.pak"), "45");
        var diffs = BackupService.VerifyDirState(modDir, before);

        Assert.Contains(diffs, d => d == "added: b.pak");
        Assert.Contains(diffs, d => d == "size-changed: a.pak");
    }

    [Fact]
    public void CreateBackup_CopiesOnlyModPaks_AndRecordsSystemPaks()
    {
        var modDir = Path.Combine(_root, "mods");
        var backupDir = Path.Combine(_root, "backup");
        Directory.CreateDirectory(modDir);
        File.WriteAllText(Path.Combine(modDir, "pakchunk0-Windows.pak"), "system");
        File.WriteAllText(Path.Combine(modDir, "pakchunk99-Mods_MyMod_P.pak"), "mod");

        var (_, manifestPath) = BackupService.CreateBackup(modDir, backupDir, backupEnabled: true);

        var manifest = JsonSerializer.Deserialize<BackupManifest>(File.ReadAllText(manifestPath))!;
        Assert.True(manifest.Files.ContainsKey("pakchunk0-Windows.pak"));
        Assert.True(manifest.Files.ContainsKey("pakchunk99-Mods_MyMod_P.pak"));
        Assert.False(File.Exists(Path.Combine(backupDir, "pakchunk0-Windows.pak")));
        Assert.True(File.Exists(Path.Combine(backupDir, "pakchunk99-Mods_MyMod_P.pak")));
    }

    [Fact]
    public void RestoreBackup_RemoveNewCleansUnexpectedMods()
    {
        var modDir = Path.Combine(_root, "mods");
        var backupDir = Path.Combine(_root, "backup");
        var restoreDir = Path.Combine(_root, "restore");
        Directory.CreateDirectory(modDir);
        Directory.CreateDirectory(restoreDir);
        File.WriteAllText(Path.Combine(modDir, "pakchunk99-Mods_MyMod_P.pak"), "mod");
        var (_, _) = BackupService.CreateBackup(modDir, backupDir, backupEnabled: true);
        File.WriteAllText(Path.Combine(restoreDir, "pakchunk99-Other_P.pak"), "new");

        var (_, removed) = BackupService.RestoreBackup(backupDir, restoreDir, removeNew: true);

        Assert.Contains("pakchunk99-Other_P.pak", removed);
        Assert.True(File.Exists(Path.Combine(restoreDir, "pakchunk99-Mods_MyMod_P.pak")));
    }

    [Theory]
    [InlineData("..")]
    [InlineData("a/b.pak")]
    [InlineData("")]
    public void SafeBasename_RejectsUnsafe(string name) =>
        Assert.False(BackupService.SafeBasename(name));
}
