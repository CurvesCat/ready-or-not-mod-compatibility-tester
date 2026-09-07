using RoNCT.Analysis;

namespace RoNCT.Tests.Analysis;

public sealed class Cue4PakTests
{
    private const string SamplePak =
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks\pakchunk99-noNVGblur_DLC2Updated_P.pak";

    [Fact]
    public void ListsAssets_OnRealSamplePak()
    {
        // Real-mod fixture: only meaningful on a machine with Ready or Not.
        if (!File.Exists(SamplePak))
        {
            return;
        }

        var inspector = new Cue4PakInspector();
        var assets = inspector.ListAssets(SamplePak);

        Assert.Contains(
            assets,
            path => path.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public void ReadFile_ReturnsSampleUassetBytes()
    {
        if (!File.Exists(SamplePak))
        {
            return;
        }

        const string inner =
            "ReadyOrNot/Content/ReadyOrNot/Assets/Advanced/Postprocess/Night_Vision/Instances/MI_NVG_Blur.uasset";

        var bytes = new Cue4PakReader().ReadFile(SamplePak, inner);

        Assert.True(bytes.Length > 100);
    }
}
