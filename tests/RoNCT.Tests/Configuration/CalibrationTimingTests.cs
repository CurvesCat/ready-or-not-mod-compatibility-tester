using RoNCT.Core.Configuration;

namespace RoNCT.Tests.Configuration;

public sealed class CalibrationTimingTests
{
    [Fact]
    public void SuggestedStableCapsAtThirtyFiveWhenMenuWasNotDetected()
    {
        Assert.Equal(
            35,
            CalibrationTiming.SuggestedStable(
                windowSeconds: 80, menuSeconds: null));
    }

    [Fact]
    public void SuggestedStableUsesMenuToWindowDeltaWhenMenuIsKnown()
    {
        Assert.Equal(
            38,
            CalibrationTiming.SuggestedStable(
                windowSeconds: 20, menuSeconds: 50));
    }

    [Fact]
    public void WindowGraceReachedAfterTenSecondsPastWindow()
    {
        Assert.False(CalibrationTiming.WindowGraceReached(
            windowSeconds: 10, elapsedSeconds: 19.9));
        Assert.True(CalibrationTiming.WindowGraceReached(
            windowSeconds: 10, elapsedSeconds: 20));
    }
}
