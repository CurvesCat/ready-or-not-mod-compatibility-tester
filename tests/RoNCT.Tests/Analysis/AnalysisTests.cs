using RoNCT.Core.Analysis;
using Xunit;

namespace RoNCT.Tests.Analysis;

public sealed class AnalysisTests
{
    [Fact]
    public void RepakListParser_SplitsAndTrimsLines()
    {
        var output = "ReadyOrNot/Content/A.uasset\n\nReadyOrNot\\Content\\B.uexp\n";
        var files = RepakListParser.Parse(output);

        Assert.Equal(2, files.Count);
        Assert.Equal("ReadyOrNot/Content/A.uasset", files[0]);
        Assert.Equal("ReadyOrNot\\Content\\B.uexp", files[1]);
    }

    [Fact]
    public void Analyze_FindsAssetsSharedAcrossMods_AsOverlaps()
    {
        var contents = new Dictionary<string, IReadOnlyList<string>>
        {
            ["a.pak"] = new[] { "Content/Shared.uasset", "Content/OnlyA.uasset" },
            ["b.pak"] = new[] { "Content/Shared.uasset", "Content/OnlyB.uasset" },
        };

        var analysis = DependencyAnalyzer.Analyze(contents);

        Assert.Equal(3, analysis.TotalAssetPaths);
        Assert.Single(analysis.Overlaps);
        Assert.Equal("Content/Shared.uasset", analysis.Overlaps[0].AssetPath);
        Assert.Equal(2, analysis.Overlaps[0].Mods.Count);
    }

    [Fact]
    public void Analyze_TreatsPathsCaseInsensitively()
    {
        var contents = new Dictionary<string, IReadOnlyList<string>>
        {
            ["a.pak"] = new[] { "content/shared.uasset" },
            ["b.pak"] = new[] { "Content/Shared.UAsset" },
        };

        var analysis = DependencyAnalyzer.Analyze(contents);

        Assert.Single(analysis.Overlaps);
    }

    [Fact]
    public void UePaths_ToGamePath_StripsContentPrefixAndExtension()
    {
        var path = "ReadyOrNot/Content/Mods/Weapons/Gun.uasset";
        Assert.Equal("/Game/Mods/Weapons/Gun", UePaths.ToGamePath(path));
    }

    [Fact]
    public void ProviderMap_MatchesReferenceAcrossMods_WithHighConfidence()
    {
        var inventories = new[]
        {
            new PakInventory("a.pak", "a.pak", new[] { "Content/Mods/Weapons/Gun.uasset" }),
            new PakInventory("b.pak", "b.pak", new[] { "Content/Mods/Weapons/Gun.uasset" }),
        };
        var map = ProviderMap.Build(inventories);

        var (mod, confidence) = ProviderMap.MatchReference("/Game/Mods/Weapons/Gun", map, "b.pak");

        Assert.Equal("a.pak", mod);
        Assert.Equal("high", confidence);
    }

    [Fact]
    public void StaticConflict_MarksOverwrite_WhenContentDiffers()
    {
        var inventories = new[]
        {
            new PakInventory("a.pak", "a.pak", new[] { "Content/Shared.uasset" }),
            new PakInventory("b.pak", "b.pak", new[] { "Content/Shared.uasset" }),
        };
        var conflicts = StaticConflictAnalyzer.Analyze(
            inventories,
            (_, _) => System.Text.Encoding.UTF8.GetBytes("version-a"));

        var conflict = Assert.Single(conflicts);
        Assert.Equal(StaticConflictKind.Duplicate, conflict.Kind);
        Assert.Equal(2, conflict.Providers.Count);
    }

    [Fact]
    public void StaticConflict_MarksDuplicate_WhenContentIdentical()
    {
        var inventories = new[]
        {
            new PakInventory("a.pak", "a.pak", new[] { "Content/Shared.uasset" }),
            new PakInventory("b.pak", "b.pak", new[] { "Content/Shared.uasset" }),
        };
        var content = System.Text.Encoding.UTF8.GetBytes("same");
        var conflicts = StaticConflictAnalyzer.Analyze(inventories, (_, _) => content);

        Assert.Equal(StaticConflictKind.Duplicate, Assert.Single(conflicts).Kind);
    }
}
