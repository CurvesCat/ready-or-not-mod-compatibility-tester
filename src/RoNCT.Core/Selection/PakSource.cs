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

        return Directory
            .EnumerateFiles(folderPath, "*.pak", SearchOption.TopDirectoryOnly)
            .OrderBy(path => Path.GetFileName(path), StringComparer.OrdinalIgnoreCase)
            .Select(ToItem)
            .ToArray();
    }

    public static IReadOnlyList<ModItem> FromFiles(IEnumerable<string> filePaths)
    {
        return filePaths
            .Where(File.Exists)
            .Where(path => string.Equals(
                Path.GetExtension(path), ".pak", StringComparison.OrdinalIgnoreCase))
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
        return !System.Text.RegularExpressions.Regex.IsMatch(
            fileName,
            @"^pakchunk[0-9]+-Windows\.pak$",
            System.Text.RegularExpressions.RegexOptions.IgnoreCase);
    }

    private static ModItem ToItem(string path)
    {
        var info = new FileInfo(path);
        return new ModItem(info.FullName, info.Name, info.Length);
    }
}
