namespace RoNCT.Core.Analysis;

public static class ProviderMap
{
    public static IReadOnlyDictionary<string, IReadOnlyList<string>> Build(
        IEnumerable<PakInventory> inventories)
    {
        var map = new Dictionary<string, List<string>>(StringComparer.OrdinalIgnoreCase);
        foreach (var inventory in inventories)
        {
            foreach (var stem in UePaths.UAssetStems(inventory.InternalPaths))
            {
                var gamePath = UePaths.ToGamePath(stem + ".uasset");
                if (!map.TryGetValue(gamePath, out var owners))
                {
                    owners = new List<string>();
                    map[gamePath] = owners;
                }
                if (!owners.Contains(inventory.FileName, StringComparer.OrdinalIgnoreCase))
                {
                    owners.Add(inventory.FileName);
                }
            }
        }
        return map.ToDictionary(
            pair => pair.Key,
            pair => (IReadOnlyList<string>)pair.Value,
            StringComparer.OrdinalIgnoreCase);
    }

    public static (string? ModName, string Confidence) MatchReference(
        string reference,
        IReadOnlyDictionary<string, IReadOnlyList<string>> providerMap,
        string currentMod)
    {
        var trimmed = reference.Trim();
        if (!trimmed.StartsWith("/Game", StringComparison.Ordinal))
        {
            return (null, string.Empty);
        }

        var refWithoutObject = trimmed.Contains(':')
            ? trimmed.Split(':', 2)[0]
            : trimmed;

        var candidates = new List<string>();
        string? exact = null;
        foreach (var providerPath in providerMap.Keys)
        {
            if (string.Equals(refWithoutObject, providerPath, StringComparison.OrdinalIgnoreCase))
            {
                exact = providerPath;
                break;
            }
            if (refWithoutObject.StartsWith(providerPath + ".", StringComparison.OrdinalIgnoreCase) ||
                refWithoutObject.StartsWith(providerPath + "_C", StringComparison.OrdinalIgnoreCase))
            {
                candidates.Add(providerPath);
            }
        }
        if (exact is not null)
        {
            candidates.Add(exact);
        }

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var candidate in candidates)
        {
            if (!providerMap.TryGetValue(candidate, out var mods))
            {
                continue;
            }
            foreach (var modName in mods)
            {
                if (string.Equals(modName, currentMod, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }
                var key = candidate + "|" + modName;
                if (!seen.Add(key))
                {
                    continue;
                }
                var confidence =
                    string.Equals(candidate, refWithoutObject, StringComparison.OrdinalIgnoreCase)
                        ? "high"
                        : "medium";
                return (modName, confidence);
            }
        }
        return (null, string.Empty);
    }
}
