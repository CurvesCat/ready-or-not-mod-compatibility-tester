using System.Text;

namespace RoNCT.App.Services;

public sealed class CalibrationResult
{
    public CalibrationResult(double? windowSeconds, double? menuSeconds, double suggestedStable)
    {
        WindowSeconds = windowSeconds;
        MenuSeconds = menuSeconds;
        SuggestedStable = suggestedStable;
    }

    public double? WindowSeconds { get; }
    public double? MenuSeconds { get; }
    public double SuggestedStable { get; }
}

public static class CalibrationService
{
    private static readonly string[] MenuMarkers =
    {
        "loading 'l_mainmenu", "loaded 'l_mainmenu", "l_mainmenu", "mainmenu",
        "main menu", "loading 'mainmenu", "loaded 'mainmenu",
    };

    public static CalibrationResult Run(
        string exePath,
        string extraArgs,
        string logDir,
        double startupTimeoutSeconds = 180,
        double maxSeconds = 120,
        Action<string>? log = null,
        CancellationToken cancellationToken = default)
    {
        log ??= _ => { };
        Directory.CreateDirectory(logDir);
        var logPath = Path.Combine(logDir, $"calib_{Guid.NewGuid():N}.log");
        using var process = GameProcessService.LaunchGame(exePath, logPath, extraArgs);
        if (process is null)
        {
            throw new InvalidOperationException("Failed to launch the game for calibration.");
        }

        log($"Calibration: launched game (PID {process.Id}).");
        var start = DateTime.UtcNow;
        double? windowAt = null;
        double? menuAt = null;
        var lastClick = DateTime.UtcNow;
        var offset = 0;

        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                var now = DateTime.UtcNow;
                var elapsed = (now - start).TotalSeconds;
                var pids = GameProcessService.FindGameProcessIds(exePath);
                var windows = GameProcessService.FindGameMainWindows(pids);

                if (windows.Count > 0 && windowAt is null)
                {
                    windowAt = elapsed;
                    log($"Calibration: main window appeared at {windowAt:0.0}s.");
                }
                if (windows.Count > 0 && windowAt is not null &&
                    (now - lastClick).TotalSeconds >= 1)
                {
                    GameProcessService.ClickWindow(windows[0].Hwnd);
                    lastClick = now;
                }

                var menuFound = ScanMenu(logPath, ref offset);
                if (menuFound && menuAt is null)
                {
                    menuAt = elapsed;
                    log($"Calibration: main-menu marker at {menuAt:0.0}s.");
                }

                if (process.HasExited)
                {
                    if (windowAt is null && elapsed >= startupTimeoutSeconds)
                    {
                        throw new InvalidOperationException("Calibration timeout: no game window appeared.");
                    }
                    break;
                }

                if (menuAt is not null && elapsed - menuAt.Value >= 2)
                {
                    break;
                }
                if (windowAt is null && elapsed >= startupTimeoutSeconds)
                {
                    throw new InvalidOperationException("Calibration timeout: no game window appeared.");
                }
                if (elapsed >= maxSeconds)
                {
                    log("Calibration: hit max seconds; using conservative value.");
                    break;
                }

                Thread.Sleep(300);
            }
        }
        finally
        {
            var pids = GameProcessService.FindGameProcessIds(exePath);
            if (pids.Count > 0)
            {
                GameProcessService.GracefulClose(pids, 6);
            }
            try
            {
                if (!process.HasExited)
                {
                    process.Kill(entireProcessTree: true);
                }
            }
            catch
            {
                // already gone
            }
        }

        var suggested = menuAt is not null && windowAt is not null
            ? Math.Max(35, menuAt.Value - windowAt.Value + 8)
            : windowAt is not null ? Math.Max(35, windowAt.Value + 15) : 35;
        return new CalibrationResult(windowAt, menuAt, suggested);
    }

    private static bool ScanMenu(string logPath, ref int offset)
    {
        if (!File.Exists(logPath))
        {
            return false;
        }
        var data = File.ReadAllBytes(logPath);
        if (data.Length <= offset)
        {
            return false;
        }
        var text = Decode(data[offset..]);
        offset = data.Length;
        var lowered = text.ToLowerInvariant();
        return MenuMarkers.Any(marker => lowered.Contains(marker, StringComparison.Ordinal));
    }

    private static string Decode(byte[] data)
    {
        if (data.Length >= 2 &&
            ((data[0] == 0xFF && data[1] == 0xFE) ||
             (data[0] == 0xFE && data[1] == 0xFF)))
        {
            return Encoding.Unicode.GetString(data);
        }
        return Encoding.UTF8.GetString(data);
    }
}
