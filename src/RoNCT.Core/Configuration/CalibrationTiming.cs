namespace RoNCT.Core.Configuration;

/// <summary>
/// Pure rules for calibration durations. The menu can be hard to detect on
/// some machines (no UE log, high CPU on the menu), so calibration falls back
/// to a short window-stability grace period instead of waiting indefinitely.
/// </summary>
public static class CalibrationTiming
{
    public const double WindowGraceSeconds = 10;
    public const double MinimumSuggestedStable = 35;

    public static double SuggestedStable(
        double? windowSeconds,
        double? menuSeconds)
    {
        if (windowSeconds is not null && menuSeconds is not null)
        {
            return Math.Max(
                MinimumSuggestedStable,
                Math.Round(menuSeconds.Value - windowSeconds.Value + 8));
        }

        return MinimumSuggestedStable;
    }

    public static bool WindowGraceReached(
        double? windowSeconds,
        double elapsedSeconds) =>
        windowSeconds is not null &&
        elapsedSeconds >= windowSeconds.Value + WindowGraceSeconds;
}
