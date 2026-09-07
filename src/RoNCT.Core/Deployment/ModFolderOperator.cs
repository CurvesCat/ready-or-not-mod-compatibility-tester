using RoNCT.Core.Selection;

namespace RoNCT.Core.Deployment;

/// <summary>
/// The only component allowed to mutate the game Mod directory. Parks mods
/// that should not be installed for a session, and restores them afterwards.
/// All parked files are kept (never deleted) under an app-managed session root.
/// Base-game pak files are never parked or restored.
/// </summary>
public sealed class ModFolderOperator
{
    private readonly string _modDir;
    private readonly string _sessionRoot;

    public ModFolderOperator(string modDir, string sessionRoot)
    {
        _modDir = modDir;
        _sessionRoot = sessionRoot;
        if (string.Equals(
            Path.GetFullPath(_modDir).TrimEnd('\\'),
            Path.GetFullPath(_sessionRoot).TrimEnd('\\'),
            StringComparison.OrdinalIgnoreCase))
        {
            throw new ArgumentException("Mod directory and session root must differ.");
        }
    }

    /// <summary>Installed (non-system) mod pak file names in the mod folder.</summary>
    public IReadOnlyList<string> InstalledModNames()
    {
        if (!Directory.Exists(_modDir))
        {
            return Array.Empty<string>();
        }

        return Directory
            .EnumerateFiles(_modDir, "*.pak", SearchOption.TopDirectoryOnly)
            .Select(Path.GetFileName)
            .Where(name => name is not null && PakSource.IsModPak(name))
            .Cast<string>()
            .OrderBy(name => name, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    /// <summary>
    /// Parks every installed mod not in <paramref name="keepFileNames"/>. The
    /// operation is preflighted and rolls back if any move fails, so a real
    /// game folder is never left half-mutated by parking.
    /// </summary>
    public IReadOnlyList<string> ParkOthers(IReadOnlyCollection<string> keepFileNames)
    {
        Directory.CreateDirectory(_modDir);
        Directory.CreateDirectory(_sessionRoot);
        var keep = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var name in keepFileNames)
        {
            keep.Add(Path.GetFileName(name));
        }

        var toPark = InstalledModNames()
            .Where(name => !keep.Contains(name))
            .ToArray();

        foreach (var name in toPark)
        {
            var destination = Path.Combine(_sessionRoot, name);
            if (File.Exists(destination))
            {
                throw new IOException(
                    $"Session folder already contains parked file: {name}. " +
                    "Restore or clear the previous session before parking again.");
            }
        }

        var moved = new List<(string Source, string Destination)>(toPark.Length);
        try
        {
            foreach (var name in toPark)
            {
                var source = Path.Combine(_modDir, name);
                var destination = Path.Combine(_sessionRoot, name);
                File.Move(source, destination, overwrite: false);
                moved.Add((source, destination));
            }
        }
        catch
        {
            for (var index = moved.Count - 1; index >= 0; index--)
            {
                var (source, destination) = moved[index];
                try
                {
                    if (File.Exists(destination) && !File.Exists(source))
                    {
                        File.Move(destination, source, overwrite: false);
                    }
                }
                catch
                {
                    // best effort rollback; the caller must inspect state
                }
            }
            throw;
        }

        return moved.Select(move => Path.GetFileName(move.Source) ?? string.Empty)
            .ToArray();
    }

    public IReadOnlyList<string> RestoreAll()
    {
        var restored = new List<string>();
        if (!Directory.Exists(_sessionRoot))
        {
            return restored;
        }

        Directory.CreateDirectory(_modDir);
        foreach (var path in Directory.EnumerateFiles(_sessionRoot, "*.pak"))
        {
            var name = Path.GetFileName(path);
            if (!PakSource.IsModPak(name) || !BackupService.SafeBasename(name))
            {
                continue;
            }
            File.Move(path, Path.Combine(_modDir, name), overwrite: true);
            restored.Add(name);
        }
        return restored;
    }
}
