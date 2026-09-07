using RoNCT.Analysis;
using RoNCT.Core.Analysis;
using RoNCT.Core.Plan;
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

public sealed class DependencyScanGraph
{
    public DependencyScanGraph(
        int paks,
        int parsedAssets,
        IReadOnlyList<DependencyEdge> edges,
        int unresolved,
        IReadOnlyList<IReadOnlyList<string>> conflictPairs,
        int conflictCount)
    {
        Paks = paks;
        ParsedAssets = parsedAssets;
        Edges = edges;
        Unresolved = unresolved;
        ConflictPairs = conflictPairs;
        ConflictCount = conflictCount;
    }

    public int Paks { get; }
    public int ParsedAssets { get; }
    public IReadOnlyList<DependencyEdge> Edges { get; }
    public int Unresolved { get; }
    public IReadOnlyList<IReadOnlyList<string>> ConflictPairs { get; }
    public int ConflictCount { get; }
}

public static class DependencyScanner
{
    public static async Task<DependencyScanResult> RunAsync(
        string? repakExe,
        string? dotnetExe,
        string? uassetCliDll,
        string engine,
        IReadOnlyList<ModItem> mods,
        int assetLimit = 100,
        CancellationToken cancellationToken = default,
        IPakInspector? pakInspector = null,
        IPakFileReader? pakFileReader = null,
        IAssetParser? assetParser = null)
    {
        var graph = await ScanGraphAsync(
            repakExe,
            dotnetExe,
            uassetCliDll,
            engine,
            mods,
            assetLimit,
            cancellationToken,
            pakInspector,
            pakFileReader,
            assetParser);
        return new DependencyScanResult(
            graph.Paks,
            graph.ParsedAssets,
            graph.Edges.Count,
            graph.Unresolved,
            graph.ConflictCount);
    }

    public static async Task<DependencyScanGraph> ScanGraphAsync(
        string? repakExe,
        string? dotnetExe,
        string? uassetCliDll,
        string engine,
        IReadOnlyList<ModItem> mods,
        int assetLimit = 100,
        CancellationToken cancellationToken = default,
        IPakInspector? pakInspector = null,
        IPakFileReader? pakFileReader = null,
        IAssetParser? assetParser = null)
    {
        var inventories = new List<PakInventory>();
        foreach (var mod in mods)
        {
            var assets = await ListAssetsSafeAsync(
                mod.FilePath, repakExe, pakInspector, cancellationToken);
            if (assets is not null)
            {
                inventories.Add(new PakInventory(mod.FilePath, mod.FileName, assets));
            }
        }

        var providerMap = ProviderMap.Build(inventories);
        var conflicts = StaticConflictAnalyzer.Analyze(
            inventories,
            (pakPath, internalPath) =>
                ReadBytesSafe(pakPath, internalPath, repakExe, pakFileReader)
                ?? Array.Empty<byte>());
        var conflictPairs = conflicts
            .Where(conflict => conflict.Kind == StaticConflictKind.Overwrite)
            .Select(conflict => (IReadOnlyList<string>)conflict.Providers
                .Select(provider => provider.PakName)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .Take(2)
                .ToArray())
            .ToArray();

        var edges = new HashSet<(string From, string To)>();
        var unresolved = 0;
        var parsedAssets = 0;
        var useInProcess = pakFileReader is not null && assetParser is not null;

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

                IReadOnlyList<string> references;
                if (useInProcess)
                {
                    var uassetBytes = ReadBytesSafe(
                        inventory.PakPath, stem + ".uasset", repakExe, pakFileReader);
                    if (uassetBytes is null)
                    {
                        continue;
                    }

                    byte[]? uexpBytes = null;
                    if (inventory.InternalPaths.Contains(
                            stem + ".uexp", StringComparer.OrdinalIgnoreCase))
                    {
                        uexpBytes = ReadBytesSafe(
                            inventory.PakPath, stem + ".uexp", repakExe, pakFileReader);
                    }

                    AssetImports? imports = null;
                    try
                    {
                        imports = assetParser!.Parse(uassetBytes, uexpBytes);
                    }
                    catch
                    {
                        imports = null;
                    }
                    if (imports is null)
                    {
                        continue;
                    }

                    parsedAssets++;
                    references = imports.ImportNames.Concat(imports.SoftReferences).ToArray();
                }
                else
                {
                    var json = await RunSubprocessParseAsync(
                        dotnetExe, uassetCliDll, repakExe, inventory, stem, engine,
                        cancellationToken);
                    if (json is null)
                    {
                        continue;
                    }

                    parsedAssets++;
                    references = CollectReferences(json).ToArray();
                }

                foreach (var reference in references)
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
        }

        var dependencyEdges = edges
            .Select(edge => new DependencyEdge(edge.From, edge.To))
            .ToArray();
        return new DependencyScanGraph(
            inventories.Count,
            parsedAssets,
            dependencyEdges,
            unresolved,
            conflictPairs,
            conflicts.Count);
    }

    private static async Task<IReadOnlyList<string>?> ListAssetsSafeAsync(
        string pakPath,
        string? repakExe,
        IPakInspector? pakInspector,
        CancellationToken cancellationToken)
    {
        if (pakInspector is not null)
        {
            try
            {
                return pakInspector.ListAssets(pakPath);
            }
            catch
            {
                return null;
            }
        }

        if (string.IsNullOrEmpty(repakExe))
        {
            return null;
        }

        return await PakLister.ListAssetsAsync(repakExe, pakPath, cancellationToken);
    }

    private static byte[]? ReadBytesSafe(
        string pakPath,
        string internalPath,
        string? repakExe,
        IPakFileReader? pakFileReader)
    {
        if (pakFileReader is not null)
        {
            try
            {
                return pakFileReader.ReadFile(pakPath, internalPath);
            }
            catch
            {
                return null;
            }
        }

        if (string.IsNullOrEmpty(repakExe))
        {
            return null;
        }

        return PakLister.ReadFileBytes(repakExe, pakPath, internalPath);
    }

    private static async Task<UAssetJson?> RunSubprocessParseAsync(
        string? dotnetExe,
        string? uassetCliDll,
        string? repakExe,
        PakInventory inventory,
        string stem,
        string engine,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrEmpty(dotnetExe) ||
            string.IsNullOrEmpty(uassetCliDll) ||
            string.IsNullOrEmpty(repakExe))
        {
            return null;
        }

        var uassetBytes = ReadBytesSafe(
            inventory.PakPath, stem + ".uasset", repakExe, pakFileReader: null);
        if (uassetBytes is null)
        {
            return null;
        }

        var tempRoot = Path.Combine(
            Path.GetTempPath(), "ronct-dep-assets", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempRoot);
        try
        {
            var fileName = Path.GetFileName(stem);
            var uassetTemp = Path.Combine(tempRoot, fileName + ".uasset");
            File.WriteAllBytes(uassetTemp, uassetBytes);

            string? uexpTemp = null;
            if (inventory.InternalPaths.Contains(
                    stem + ".uexp", StringComparer.OrdinalIgnoreCase))
            {
                var uexpBytes = ReadBytesSafe(
                    inventory.PakPath, stem + ".uexp", repakExe, pakFileReader: null);
                if (uexpBytes is not null)
                {
                    uexpTemp = Path.Combine(tempRoot, fileName + ".uexp");
                    File.WriteAllBytes(uexpTemp, uexpBytes);
                }
            }

            return await UAssetCliService.ToJsonAsync(
                dotnetExe, uassetCliDll, uassetTemp, uexpTemp, engine, cancellationToken);
        }
        finally
        {
            try { Directory.Delete(tempRoot, recursive: true); }
            catch { /* best effort */ }
        }
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
