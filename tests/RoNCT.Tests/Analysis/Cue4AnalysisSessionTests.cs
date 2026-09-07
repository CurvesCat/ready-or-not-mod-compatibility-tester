using RoNCT.Analysis;

namespace RoNCT.Tests.Analysis;

public sealed class Cue4AnalysisSessionTests
{
    private const string SamplePak =
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks\pakchunk99-noNVGblur_DLC2Updated_P.pak";

    private const string SampleUasset =
        "ReadyOrNot/Content/ReadyOrNot/Assets/Advanced/Postprocess/Night_Vision/Instances/MI_NVG_Blur.uasset";

    [Fact]
    public void ReusedSession_ListsAndReadsRealPakTwice()
    {
        if (!File.Exists(SamplePak))
        {
            return;
        }

        using var session = new Cue4AnalysisSession();

        var firstList = session.ListAssets(SamplePak);
        var firstBytes = session.ReadFile(SamplePak, SampleUasset);
        var secondList = session.ListAssets(SamplePak);
        var secondBytes = session.ReadFile(SamplePak, SampleUasset);

        Assert.Equal(firstList, secondList);
        Assert.Equal(firstBytes, secondBytes);
        Assert.True(firstBytes.Length > 100);
    }
}
