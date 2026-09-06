namespace RoNCT.Core.Analysis;

public sealed record AssetOverlap(string AssetPath, IReadOnlyList<string> Mods);

public sealed class AssetAnalysis
{
    public AssetAnalysis(
        IReadOnlyDictionary<string, IReadOnlyList<string>> assetsToMods,
        IReadOnlyList<AssetOverlap> overlaps)
    {
        AssetsToMods = assetsToMods;
        Overlaps = overlaps;
    }

    public IReadOnlyDictionary<string, IReadOnlyList<string>> AssetsToMods { get; }
    public IReadOnlyList<AssetOverlap> Overlaps { get; }

    public int TotalAssetPaths => AssetsToMods.Count;
}

public static class DependencyAnalyzer
{
    public static AssetAnalysis Analyze(
        IReadOnlyDictionary<string, IReadOnlyList<string>> pakContents)
    {
        var assetsToMods = new Dictionary<string, List<string>>(
            StringComparer.OrdinalIgnoreCase);

        foreach (var (pak, assets) in pakContents)
        {
            foreach (var asset in assets)
            {
                var normalized = Normalize(asset);
                if (normalized.Length == 0)
                {
                    continue;
                }

                if (!assetsToMods.TryGetValue(normalized, out var owners))
                {
                    owners = new List<string>();
                    assetsToMods[normalized] = owners;
                }

                if (!owners.Contains(pak, StringComparer.OrdinalIgnoreCase))
                {
                    owners.Add(pak);
                }
            }
        }

        var overlaps = assetsToMods
            .Where(pair => pair.Value.Count > 1)
            .Select(pair => new AssetOverlap(pair.Key, pair.Value.ToArray()))
            .OrderBy(overlap => overlap.AssetPath, StringComparer.OrdinalIgnoreCase)
            .ToArray();

        return new AssetAnalysis(
            assetsToMods.ToDictionary(
                pair => pair.Key, pair => (IReadOnlyList<string>)pair.Value.ToArray(),
                StringComparer.OrdinalIgnoreCase),
            overlaps);
    }

    private static string Normalize(string assetPath)
    {
        var normalized = assetPath.Replace('\\', '/');
        return normalized.Trim();
    }
}
