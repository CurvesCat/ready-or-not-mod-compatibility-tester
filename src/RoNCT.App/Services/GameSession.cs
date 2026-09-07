using System.Text;

namespace RoNCT.App.Services;

public enum TestVerdict
{
    Ok,
    Fail,
    Error,
    Conflict,
    Skipped,
}

public sealed class SessionResult
{
    public SessionResult(
        TestVerdict verdict,
        string reason,
        string excerpt,
        bool menuReached,
        double elapsedSeconds,
        IReadOnlyList<string> crashDirs)
    {
        Verdict = verdict;
        Reason = reason;
        Excerpt = excerpt;
        MenuReached = menuReached;
        ElapsedSeconds = elapsedSeconds;
        CrashDirs = crashDirs;
    }

    public TestVerdict Verdict { get; }
    public string Reason { get; }
    public string Excerpt { get; }
    public bool MenuReached { get; }
    public double ElapsedSeconds { get; }
    public IReadOnlyList<string> CrashDirs { get; }
}

/// <summary>
/// Deploys one test group, launches the game once, observes the UnrealWindow,
/// the UE log and crash-reports folder, then restores the mod folder.
/// Ported from the Python engine.py GameSession.
/// </summary>
public sealed class GameSession
{
    private static readonly string[] MenuMarkers =
    {
        "loading 'l_mainmenu", "loaded 'l_mainmenu", "l_mainmenu", "mainmenu",
        "main menu", "loading 'mainmenu", "loaded 'mainmenu",
    };

    private static readonly string[] FatalMarkers =
    {
        "fatal error", "lowlevelfatalerror", "assertion failed", "unhandled exception",
        "critical error", "exception_access_violation", "the application crashed", "apperror",
    };

    private static readonly string[] ModErrorMarkers =
    {
        "logpakfile: error", "failed to mount", "loglinker: error", "logstreaming: error",
        "loguobjectglobals: error", "logclass: error",
    };

    private readonly string _exePath;
    private readonly string _modDir;
    private readonly string _logDir;
    private readonly string? _crashesDir;
    private readonly double _stableSeconds;
    private readonly double _startupTimeout;
    private readonly double _menuHoldSeconds;
    private readonly string _extraArgs;
    private readonly Action<string> _emitLog;
    private readonly CancellationToken _cancel;
    private readonly List<string> _deployed = new();
    private System.Diagnostics.Process? _entryProcess;

    public GameSession(
        string exePath,
        string modDir,
        string logDir,
        string? crashesDir,
        double stableSeconds,
        double startupTimeout,
        double menuHoldSeconds,
        string extraArgs,
        Action<string> emitLog,
        CancellationToken cancel)
    {
        _exePath = exePath;
        _modDir = modDir;
        _logDir = logDir;
        _crashesDir = crashesDir;
        _stableSeconds = stableSeconds;
        _startupTimeout = startupTimeout;
        _menuHoldSeconds = menuHoldSeconds;
        _extraArgs = extraArgs;
        _emitLog = emitLog;
        _cancel = cancel;
    }

    public SessionResult Run(IReadOnlyList<DeploySource> items, string label)
    {
        Directory.CreateDirectory(_logDir);
        var safeLabel =
            $"session_{DateTimeOffset.Now.ToUnixTimeSeconds()}_{Guid.NewGuid().ToString("N")[..8]}";

        foreach (var item in items)
        {
            var target = Path.Combine(_modDir, item.TargetName);
            if (File.Exists(target))
            {
                return new SessionResult(
                    TestVerdict.Conflict,
                    $"Mod folder already contains: {item.TargetName}",
                    string.Empty, false, 0, Array.Empty<string>());
            }
        }

        try
        {
            foreach (var item in items)
            {
                var target = Path.Combine(_modDir, item.TargetName);
                File.Copy(item.SourcePath, target, overwrite: false);
                _deployed.Add(target);
            }
        }
        catch (Exception exc)
        {
            CleanupDeployed();
            return new SessionResult(
                TestVerdict.Error, $"Failed to copy mod: {exc.Message}",
                string.Empty, false, 0, Array.Empty<string>());
        }

        var logPath = Path.Combine(_logDir, safeLabel + ".log");
        var crashBaseline = CrashBaseline();
        var result = LaunchAndMonitor(logPath, crashBaseline);
        CleanupDeployed();
        return result;
    }

    private SessionResult LaunchAndMonitor(string logPath, HashSet<string> crashBaseline)
    {
        using var process = GameProcessService.LaunchGame(_exePath, logPath, _extraArgs);
        if (process is null)
        {
            return new SessionResult(
                TestVerdict.Error, "Failed to launch the game process.",
                string.Empty, false, 0, Array.Empty<string>());
        }
        _entryProcess = process;

        _emitLog($"  Launched game (PID {process.Id})...");
        AppLog.Log($"GameSession: launched PID {process.Id} for '{logPath}'");
        var start = DateTime.UtcNow;
        var startupDeadline = start.AddSeconds(_startupTimeout);
        DateTime? windowAt = null;
        DateTime? menuAt = null;
        DateTime? stableDeadline = null;
        var lastObsLog = start;
        var lastClick = start;
        nint mainHwnd = 0;
        var clicks = 0;
        var tail = new List<string>();
        var logOffset = 0;

        while (!_cancel.IsCancellationRequested)
        {
            var pids = GameProcessService.FindGameProcessIds(_exePath);
            var alive = pids.Count > 0;
            var now = DateTime.UtcNow;
            var windows = GameProcessService.FindGameMainWindows(pids);

            if (windows.Count > 0 && windowAt is null)
            {
                windowAt = now;
                stableDeadline = now.AddSeconds(_stableSeconds);
                mainHwnd = windows[0].Hwnd;
                _emitLog("  Game main window appeared, observing...");
            }

            if (windowAt is not null && windows.Count > 0 &&
                now - windowAt.Value >= TimeSpan.FromSeconds(2) &&
                now - lastClick >= TimeSpan.FromSeconds(1) &&
                mainHwnd != 0)
            {
                GameProcessService.ClickWindow(mainHwnd);
                clicks++;
                lastClick = now;
            }

            if (windowAt is not null && menuAt is null &&
                now - lastObsLog >= TimeSpan.FromSeconds(10))
            {
                _emitLog(
                    $"  Observing... {(now - windowAt.Value).TotalSeconds:0}s / {_stableSeconds:0}s");
                lastObsLog = now;
            }

            var errorWindows = GameProcessService.FindErrorWindows(
                new[] { "RoNCT" });
            if (errorWindows.Count > 0)
            {
                var titles = string.Join("; ", errorWindows.Take(3).Select(w => w.Title));
                return Finish(logPath, TestVerdict.Fail,
                    "Detected an error dialog: " + titles, string.Empty, start);
            }

            var (newOffset, newTail, fatal, menuFound) =
                ScanLog(logPath, logOffset, tail);
            logOffset = newOffset;
            tail = newTail;
            if (fatal is not null)
            {
                return Finish(logPath, TestVerdict.Fail,
                    "Fatal/load error in the game log", fatal, start);
            }
            if (menuFound && menuAt is null)
            {
                menuAt = now;
                _emitLog("  Detected main-menu marker, entering confirmation window...");
            }

            var newCrash = NewCrashDirs(crashBaseline);
            if (newCrash.Count > 0)
            {
                return Finish(logPath, TestVerdict.Fail,
                    "Generated a crash report: " + string.Join(", ", newCrash),
                    string.Join("\n", tail.TakeLast(12)), start, newCrash);
            }

            if (!alive)
            {
                if (windowAt is null)
                {
                    if (now >= startupDeadline)
                    {
                        return Finish(logPath, TestVerdict.Error,
                            $"Startup timeout ({_startupTimeout}s) or game process never appeared.",
                            string.Empty, start);
                    }
                }
                else
                {
                    return Finish(logPath, TestVerdict.Fail,
                        $"Game exited {(now - windowAt.Value).TotalSeconds:0.0}s after startup, likely a crash.",
                        string.Join("\n", tail.TakeLast(12)), start);
                }
            }
            else
            {
                if (windowAt is null)
                {
                    if (now >= startupDeadline)
                    {
                        return Finish(logPath, TestVerdict.Error,
                            $"Process alive but no main window within {_startupTimeout}s (stuck loading).",
                            string.Empty, start);
                    }
                }
                else if (menuAt is not null)
                {
                    if (now - menuAt.Value >= TimeSpan.FromSeconds(_menuHoldSeconds))
                    {
                        return Finish(logPath, TestVerdict.Ok,
                            "Stable after the main-menu marker",
                            string.Join("\n", tail.TakeLast(12)), start, menuReached: true);
                    }
                }
                else if (stableDeadline is not null && now >= stableDeadline.Value)
                {
                    if (windows.Count > 0)
                    {
                        return Finish(logPath, TestVerdict.Ok,
                            "Game main window stayed stable",
                            string.Join("\n", tail.TakeLast(12)), start);
                    }
                }
            }

            Thread.Sleep(250);
        }

        return Finish(logPath, TestVerdict.Skipped, "Cancelled by user", string.Empty, start);
    }

    private SessionResult Finish(
        string logPath,
        TestVerdict verdict,
        string reason,
        string excerpt,
        DateTime start,
        IReadOnlyList<string>? crashDirs = null,
        bool menuReached = false)
    {
        var pids = GameProcessService.FindGameProcessIds(_exePath);
        if (pids.Count > 0)
        {
            GameProcessService.GracefulClose(pids);
        }
        try
        {
            if (_entryProcess is { HasExited: false } p)
            {
                p.Kill(entireProcessTree: true);
            }
        }
        catch
        {
            // already exited
        }
        _entryProcess = null;
        Thread.Sleep(200);
        AppLog.Log($"GameSession: verdict={verdict} reason=\"{reason}\"");
        return new SessionResult(
            verdict, reason, excerpt.Trim(), menuReached,
            (DateTime.UtcNow - start).TotalSeconds, crashDirs ?? Array.Empty<string>());
    }

    private HashSet<string> CrashBaseline()
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (_crashesDir is not null && Directory.Exists(_crashesDir))
        {
            foreach (var dir in Directory.EnumerateDirectories(_crashesDir))
            {
                set.Add(Path.GetFileName(dir));
            }
        }
        return set;
    }

    private List<string> NewCrashDirs(HashSet<string> baseline)
    {
        var result = new List<string>();
        if (_crashesDir is not null && Directory.Exists(_crashesDir))
        {
            foreach (var dir in Directory.EnumerateDirectories(_crashesDir))
            {
                var name = Path.GetFileName(dir);
                if (!baseline.Contains(name))
                {
                    result.Add(name);
                }
            }
        }
        result.Sort(StringComparer.OrdinalIgnoreCase);
        return result;
    }

    private void CleanupDeployed()
    {
        foreach (var path in _deployed)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch { /* best effort */ }
        }
        _deployed.Clear();
    }

    private static (int NewOffset, List<string> Tail, string? Fatal, bool Menu) ScanLog(
        string logPath,
        int offset,
        List<string> tail)
    {
        if (!File.Exists(logPath))
        {
            return (offset, tail, null, false);
        }

        byte[] data;
        try
        {
            data = File.ReadAllBytes(logPath);
        }
        catch
        {
            return (offset, tail, null, false);
        }
        if (data.Length <= offset)
        {
            return (offset, tail, null, false);
        }

        var text = DecodeLog(data[offset..]);
        var newOffset = data.Length;
        var lines = text.Split('\n').Select(line => line.TrimEnd('\r')).ToList();
        tail = tail.Concat(lines).TakeLast(25).ToList();
        var lowered = text.ToLowerInvariant();

        string? fatal = null;
        foreach (var marker in FatalMarkers.Concat(ModErrorMarkers))
        {
            var idx = lowered.IndexOf(marker, StringComparison.Ordinal);
            if (idx >= 0)
            {
                var start = Math.Max(0, idx - 200);
                var end = Math.Min(text.Length, idx + 400);
                fatal = text[start..end].Trim();
                break;
            }
        }

        var menu = MenuMarkers.Any(marker => lowered.Contains(marker, StringComparison.Ordinal));
        return (newOffset, tail, fatal, menu);
    }

    private static string DecodeLog(byte[] data)
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

public sealed record DeploySource(string SourcePath, string TargetName);
