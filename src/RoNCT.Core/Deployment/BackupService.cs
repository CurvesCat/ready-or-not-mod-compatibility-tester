using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using RoNCT.Core.Selection;

namespace RoNCT.Core.Deployment;

public sealed class ModDirEntry
{
    public long Size { get; set; }
    public long Mtime { get; set; }
    public bool IsDir { get; set; }
    public string? Sha256 { get; set; }
}

public sealed class BackupManifest
{
    public string CreatedAt { get; set; } = string.Empty;
    public string ModDir { get; set; } = string.Empty;
    public bool BackupEnabled { get; set; }
    public Dictionary<string, ModDirEntry> Files { get; set; } = new();
}

public static class BackupService
{
    public const string ManifestName = "manifest.json";

    public static Dictionary<string, ModDirEntry> SnapshotModDir(string modDir)
    {
        var snapshot = new Dictionary<string, ModDirEntry>(StringComparer.OrdinalIgnoreCase);
        if (!Directory.Exists(modDir))
        {
            return snapshot;
        }

        foreach (var path in Directory.EnumerateFileSystemEntries(modDir))
        {
            var name = Path.GetFileName(path);
            if (Directory.Exists(path))
            {
                snapshot[name + "/"] = new ModDirEntry { IsDir = true };
            }
            else
            {
                var info = new FileInfo(path);
                snapshot[name] = new ModDirEntry
                {
                    Size = info.Length,
                    Mtime = (long)(info.LastWriteTimeUtc - DateTime.UnixEpoch).TotalSeconds,
                };
            }
        }
        return snapshot;
    }

    public static (string BackupDir, string ManifestPath) CreateBackup(
        string modDir,
        string backupRoot,
        bool backupEnabled,
        long maxFileBytes = 1_500_000_000,
        long maxTotalBytes = 10_000_000_000)
    {
        Directory.CreateDirectory(backupRoot);

        if (backupEnabled)
        {
            foreach (var old in Directory.EnumerateFileSystemEntries(backupRoot))
            {
                try
                {
                    if (File.Exists(old))
                    {
                        File.Delete(old);
                    }
                }
                catch
                {
                    // best effort
                }
            }
        }

        var manifest = new BackupManifest
        {
            CreatedAt = DateTime.Now.ToString("s"),
            ModDir = modDir,
            BackupEnabled = backupEnabled,
            Files = new Dictionary<string, ModDirEntry>(StringComparer.OrdinalIgnoreCase),
        };

        if (Directory.Exists(modDir))
        {
            long total = 0;
            foreach (var path in Directory.EnumerateFileSystemEntries(modDir).ToArray())
            {
                try
                {
                    var name = Path.GetFileName(path);
                    if (Directory.Exists(path))
                    {
                        manifest.Files[name + "/"] = new ModDirEntry { IsDir = true };
                        continue;
                    }
                    if (!SafeBasename(name))
                    {
                        continue;
                    }

                    var info = new FileInfo(path);
                    var entry = new ModDirEntry
                    {
                        Size = info.Length,
                        Mtime = (long)(info.LastWriteTimeUtc - DateTime.UnixEpoch).TotalSeconds,
                    };
                    manifest.Files[name] = entry;

                    if (backupEnabled && PakSource.IsModPak(name) &&
                        info.Length <= maxFileBytes &&
                        total + info.Length <= maxTotalBytes)
                    {
                        File.Copy(path, Path.Combine(backupRoot, name), overwrite: true);
                        using var stream = File.OpenRead(path);
                        entry.Sha256 = Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
                        total += info.Length;
                    }
                }
                catch (IOException)
                {
                    // skip a file that cannot be read; continue the rest
                }
                catch (UnauthorizedAccessException)
                {
                    // skip access-denied files
                }
            }
        }

        var manifestPath = Path.Combine(backupRoot, ManifestName);
        File.WriteAllText(
            manifestPath,
            JsonSerializer.Serialize(manifest, new JsonSerializerOptions { WriteIndented = true }));
        return (backupRoot, manifestPath);
    }

    public static (List<string> Restored, List<string> Removed) RestoreBackup(
        string backupDir,
        string modDir,
        bool removeNew)
    {
        var manifestPath = Path.Combine(backupDir, ManifestName);
        if (!File.Exists(manifestPath))
        {
            throw new FileNotFoundException($"Backup manifest not found: {manifestPath}");
        }

        var manifest = JsonSerializer.Deserialize<BackupManifest>(File.ReadAllText(manifestPath))
            ?? new BackupManifest();
        Directory.CreateDirectory(modDir);

        var restored = new List<string>();
        foreach (var (name, entry) in manifest.Files)
        {
            if (entry.IsDir || !SafeBasename(name))
            {
                continue;
            }
            var source = Path.Combine(backupDir, name);
            if (File.Exists(source))
            {
                try
                {
                    File.Copy(source, Path.Combine(modDir, name), overwrite: true);
                    restored.Add(name);
                }
                catch (IOException)
                {
                    // skip
                }
            }
        }

        var removed = new List<string>();
        if (removeNew && Directory.Exists(modDir))
        {
            foreach (var path in Directory.EnumerateFiles(modDir, "*.pak"))
            {
                var name = Path.GetFileName(path);
                if (PakSource.IsModPak(name) &&
                    !manifest.Files.ContainsKey(name))
                {
                    try
                    {
                        File.Delete(path);
                        removed.Add(name);
                    }
                    catch (IOException)
                    {
                        // skip
                    }
                }
            }
        }
        return (restored, removed);
    }

    public static List<string> VerifyDirState(
        string modDir,
        IReadOnlyDictionary<string, ModDirEntry> before)
    {
        var after = SnapshotModDir(modDir);
        var diffs = new List<string>();
        foreach (var name in before.Keys.Union(after.Keys, StringComparer.OrdinalIgnoreCase)
                     .OrderBy(n => n, StringComparer.OrdinalIgnoreCase))
        {
            if (!before.ContainsKey(name))
            {
                diffs.Add($"added: {name}");
            }
            else if (!after.ContainsKey(name))
            {
                diffs.Add($"missing: {name}");
            }
            else
            {
                var b = before[name];
                var a = after[name];
                if (b.IsDir || a.IsDir)
                {
                    if (b.IsDir != a.IsDir)
                    {
                        diffs.Add($"type-changed: {name}");
                    }
                    continue;
                }
                if (b.Size != a.Size)
                {
                    diffs.Add($"size-changed: {name}");
                }
            }
        }
        return diffs;
    }

    public static bool SafeBasename(string name) =>
        !string.IsNullOrEmpty(name) &&
        name is not "." and not ".." &&
        !name.Contains('/') &&
        !name.Contains('\\') &&
        !name.Contains("..");

    public static string Sha256(byte[] data) =>
        Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
}
