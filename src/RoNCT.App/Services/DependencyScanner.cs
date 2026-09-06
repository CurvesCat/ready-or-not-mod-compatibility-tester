using RoNCT.Core.Analysis;
using RoNCT.Core.Selection;

namespace RoNCT.App.Services;

public sealed class DependencyScanResult
{
    public DependencyScanResult(int paks, int parsedAssets, int edges, int unresolved, int conflicts)
    {
        Paks = paks;
        ParsedAssets = parsedAssets;
        Edges = edges;
        Unresolved = unresolved;
        Conflicts = conflicts;
    }

    public int Paks { get; }
    public int ParsedAssets { get; }
    public int Edges { get; }
    public int Unresolved { get; }
    public int Conflicts { get; }
}

public static class DependencyScanner
{
    public static async Task<DependencyScanResult> RunAsync(
        string repakExe,
        string dotnetExe,
        string uassetCliDll,
        string engine,
        IReadOnlyList<ModItem> mods,
        int assetLimit = 100,
        CancellationToken cancellationToken = default)
    {
        var inventories = new List<PakInventory>();
        foreach (var mod in mods)
        {
            var assets = await PakLister.ListAssetsAsync(
                repakExe, mod.FilePath, cancellationToken);
            if (assets is not null)
            {
                inventories.Add(new PakInventory(mod.FilePath, mod.FileName, assets));
            }
        }

        var providerMap = ProviderMap.Build(inventories);
        var conflicts = StaticConflictAnalyzer.Analyze(
            inventories,
            (pakPath, internalPath) =>
                PakLister.ReadFileBytes(repakExe, pakPath, internalPath)
                ?? Array.Empty<byte>());

        var edges = new HashSet<(string From, string To)>();
        var unresolved = 0;
        var parsedAssets = 0;

        foreach (var inventory in inventories)
        {
            var stems = UePaths.UAssetStems(inventory.InternalPaths)
                .Take(assetLimit > 0 ? assetLimit : int.MaxValue)
                .ToArray();

            foreach (var stem in stems)
            {
                if (cancellationToken.IsCancellationRequested)
                {
                    break;
                }

                var tempRoot = Path.Combine(
                    Path.GetTempPath(), "ronct-dep-assets", Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(tempRoot);
                try
                {
                    var uassetName = Path.GetFileName(stem) + ".uasset";
                    var uassetBytes = PakLister.ReadFileBytes(
                        repakExe, inventory.PakPath, stem + ".uasset", cancellationToken);
                    if (uassetBytes is null)
                    {
                        continue;
                    }
                    var uassetTemp = Path.Combine(tempRoot, uassetName);
                    File.WriteAllBytes(uassetTemp, uassetBytes);

                    string? uexpTemp = null;
                    if (inventory.InternalPaths.Contains(
                            stem + ".uexp", StringComparer.OrdinalIgnoreCase))
                    {
                        var uexpBytes = PakLister.ReadFileBytes(
                            repakExe, inventory.PakPath, stem + ".uexp", cancellationToken);
                        if (uexpBytes is not null)
                        {
                            uexpTemp = Path.Combine(tempRoot, Path.GetFileName(stem) + ".uexp");
                            File.WriteAllBytes(uexpTemp, uexpBytes);
                        }
                    }

                    var json = await UAssetCliService.ToJsonAsync(
                        dotnetExe, uassetCliDll, uassetTemp, uexpTemp, engine, cancellationToken);
                    if (json is null)
                    {
                        continue;
                    }
                    parsedAssets++;

                    foreach (var reference in CollectReferences(json))
                    {
                        var (mod, _) = ProviderMap.MatchReference(
                            reference, providerMap, inventory.FileName);
                        if (mod is not null)
                        {
                            edges.Add(
                                (inventory.FileName.ToLowerInvariant(),
                                 mod.ToLowerInvariant()));
                        }
                        else if (reference.StartsWith("/Game/Mods/", StringComparison.Ordinal))
                        {
                            unresolved++;
                        }
                    }
                }
                finally
                {
                    try { Directory.Delete(tempRoot, recursive: true); }
                    catch { /* best effort */ }
                }
            }
        }

        return new DependencyScanResult(
            inventories.Count, parsedAssets, edges.Count, unresolved, conflicts.Count);
    }

    private static IEnumerable<string> CollectReferences(UAssetJson json)
    {
        foreach (var import in json.Imports ?? new List<UAssetImport>())
        {
            var name = import.ObjectName;
            if (!string.IsNullOrEmpty(name) && UePaths.IsGameReference(name))
            {
                yield return name;
            }
        }

        foreach (var soft in json.SoftPackageReferenceList ?? new List<string>())
        {
            if (UePaths.IsGameReference(soft))
            {
                yield return soft;
            }
        }
    }
}
