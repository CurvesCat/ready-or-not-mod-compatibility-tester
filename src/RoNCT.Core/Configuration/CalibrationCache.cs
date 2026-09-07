namespace RoNCT.Core.Configuration;

/// <summary>
/// Decides whether an existing calibration result can be reused for the
/// current executable and launch arguments.
/// </summary>
public static class CalibrationCache
{
    public const int MaxAgeDays = 7;

    public static bool IsCurrent(
        AppConfig config,
        string exePath,
        string extraArgs,
        DateTime utcNow)
    {
        if (string.IsNullOrEmpty(config.CalibrationExePath) ||
            config.CalibrationUtc == default)
        {
            return false;
        }

        if (!string.Equals(
                config.CalibrationExePath,
                exePath,
                StringComparison.OrdinalIgnoreCase) ||
            !string.Equals(
                config.CalibrationExtraArgs ?? string.Empty,
                extraArgs ?? string.Empty,
                StringComparison.Ordinal))
        {
            return false;
        }

        return utcNow - config.CalibrationUtc <
            TimeSpan.FromDays(MaxAgeDays);
    }

    public static void Mark(
        AppConfig config,
        string exePath,
        string extraArgs,
        DateTime utcNow)
    {
        config.CalibrationExePath = exePath;
        config.CalibrationExtraArgs = extraArgs ?? string.Empty;
        config.CalibrationUtc = utcNow;
    }
}
