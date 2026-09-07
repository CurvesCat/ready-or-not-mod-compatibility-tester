namespace RoNCT.Core.Selection;

public sealed record ModItem(string FilePath, string FileName, long SizeBytes);

public static class PakSource
{
    private static readonly string[] ModSubFolders = { "mod.io", "~Mods", "Mods" };

    public static IReadOnlyList<ModItem> FromFolder(string folderPath)
    {
        if (!Directory.Exists(folderPath))
        {
            return Array.Empty<ModItem>();
        }

        var root = Path.GetFullPath(folderPath);
        var pending = new Stack<string>();
        pending.Push(root);
        var files = new List<string>();

        while (pending.Count > 0)
        {
            var current = pending.Pop();
            try
            {
                foreach (var sub in Directory.EnumerateDirectories(current))
                {
                    var attributes = File.GetAttributes(sub);
                    if ((attributes & FileAttributes.ReparsePoint) != 0)
                    {
                        // Never follow junctions/symlinks outside the folder.
                        continue;
                    }
                    var fullSub = Path.GetFullPath(sub);
                    if (fullSub.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                    {
                        pending.Push(fullSub);
                    }
                }
                files.AddRange(
                    Directory.EnumerateFiles(current, "*.pak"));
            }
            catch (IOException)
            {
                // Skip a directory that cannot be read.
            }
            catch (UnauthorizedAccessException)
            {
                // Skip access-denied directories.
            }
        }

        return files
            .Where(path => IsModPak(Path.GetFileName(path)))
            .Select(ToItem)
            .OrderBy(item => item.FileName, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    public static IReadOnlyList<ModItem> FromFiles(IEnumerable<string> filePaths)
    {
        return filePaths
            .Where(File.Exists)
            .Where(path => string.Equals(
                Path.GetExtension(path), ".pak", StringComparison.OrdinalIgnoreCase))
            .Where(path => IsModPak(Path.GetFileName(path)))
            .Select(ToItem)
            .ToArray();
    }

    public static IReadOnlyList<ModItem> FromGamePaksFolder(string gamePaksPath)
    {
        if (!Directory.Exists(gamePaksPath))
        {
            return Array.Empty<ModItem>();
        }

        var mods = Directory
            .EnumerateFiles(gamePaksPath, "*.pak", SearchOption.TopDirectoryOnly)
            .Where(path => IsModPak(Path.GetFileName(path)));

        foreach (var subFolder in ModSubFolders)
        {
            var subPath = Path.Combine(gamePaksPath, subFolder);
            if (!Directory.Exists(subPath))
            {
                continue;
            }

            mods = mods.Concat(
                Directory.EnumerateFiles(subPath, "*.pak", SearchOption.TopDirectoryOnly));
        }

        return mods
            .Select(ToItem)
            .OrderBy(item => item.FileName, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    public static bool IsModPak(string fileName)
    {
        return fileName.EndsWith(".pak", StringComparison.OrdinalIgnoreCase) &&
            !System.Text.RegularExpressions.Regex.IsMatch(
                fileName,
                @"^pakchunk[0-9]+-Windows(?:NoEditor)?(?:_.*)?\.pak$",
                System.Text.RegularExpressions.RegexOptions.IgnoreCase);
    }

    private static ModItem ToItem(string path)
    {
        var info = new FileInfo(path);
        return new ModItem(info.FullName, info.Name, info.Length);
    }
}
