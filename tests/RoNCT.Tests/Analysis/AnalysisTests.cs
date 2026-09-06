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
}
