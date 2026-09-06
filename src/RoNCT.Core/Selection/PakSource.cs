namespace RoNCT.Core.Selection;

public sealed record ModItem(string FilePath, string FileName, long SizeBytes);

public static class PakSource
{
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

    private static ModItem ToItem(string path)
    {
        var info = new FileInfo(path);
        return new ModItem(info.FullName, info.Name, info.Length);
    }
}
