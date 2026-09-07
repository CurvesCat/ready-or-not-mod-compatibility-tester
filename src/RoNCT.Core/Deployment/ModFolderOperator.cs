namespace RoNCT.Core.Deployment;

/// <summary>
/// The only component allowed to mutate the game Mod directory. Parks mods
/// that should not be installed for a session, and restores them afterwards.
/// All parked files are kept (never deleted) under an app-managed session root.
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

    public IReadOnlyList<string> ParkOthers(IReadOnlyCollection<string> keepFileNames)
    {
        Directory.CreateDirectory(_modDir);
        Directory.CreateDirectory(_sessionRoot);
        var keep = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var name in keepFileNames)
        {
            keep.Add(Path.GetFileName(name));
        }

        var parked = new List<string>();
        foreach (var path in Directory.EnumerateFiles(_modDir, "*.pak"))
        {
            var name = Path.GetFileName(path);
            if (keep.Contains(name))
            {
                continue;
            }
            var destination = Path.Combine(_sessionRoot, name);
            File.Move(path, destination, overwrite: true);
            parked.Add(name);
        }
        return parked;
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
            File.Move(path, Path.Combine(_modDir, name), overwrite: true);
            restored.Add(name);
        }
        return restored;
    }
}
