using RoNCT.Analysis;

namespace RoNCT.Tests.Analysis;

public sealed class Cue4AssetParserTests
{
    private const string SamplePak =
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks\pakchunk99-noNVGblur_DLC2Updated_P.pak";

    private const string SampleUasset =
        "ReadyOrNot/Content/ReadyOrNot/Assets/Advanced/Postprocess/Night_Vision/Instances/MI_NVG_Blur.uasset";

    [Fact]
    public void ParsesImportTable_OnRealSampleAsset()
    {
        if (!File.Exists(SamplePak))
        {
            return;
        }

        var uasset = new Cue4PakReader().ReadFile(SamplePak, SampleUasset);
        var parser = new Cue4AssetParser();

        var imports = parser.Parse(uasset, uexp: null);

        Assert.Contains(
            imports.ImportNames,
            name => name.StartsWith("/Game", StringComparison.Ordinal));
    }
}
