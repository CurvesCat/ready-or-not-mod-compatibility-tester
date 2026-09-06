namespace RoNCT.Core.Analysis;

public static class UePaths
{
    private static readonly string[] ContentPrefixes = { "ReadyOrNot/Content/", "Content/" };
    private static readonly string[] AssetSuffixes = { ".uasset", ".uexp", ".ubulk", ".uptnl" };

    public static string ToGamePath(string pakPath)
    {
        var normalized = pakPath.Replace('\\', '/');
        foreach (var prefix in ContentPrefixes)
        {
            if (normalized.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                var stem = normalized[prefix.Length..];
                foreach (var suffix in AssetSuffixes)
                {
                    if (stem.EndsWith(suffix, StringComparison.OrdinalIgnoreCase))
                    {
                        stem = stem[..^suffix.Length];
                        break;
                    }
                }
                return "/Game/" + stem;
            }
        }
        return normalized;
    }

    public static IEnumerable<string> UAssetStems(IEnumerable<string> internalPaths)
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var path in internalPaths)
        {
            if (path.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase))
            {
                set.Add(path[..^".uasset".Length]);
            }
        }
        return set.OrderBy(stem => stem, StringComparer.OrdinalIgnoreCase);
    }

    public static bool IsGameReference(string reference) =>
        reference.StartsWith("/Game", StringComparison.Ordinal) ||
        reference.StartsWith("/ReadyOrNot", StringComparison.Ordinal);
}
