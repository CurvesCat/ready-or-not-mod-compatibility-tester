using System.Diagnostics;
using System.Runtime.InteropServices;

namespace RoNCT.App.Services;

/// <summary>
/// Win32 helpers ported from the Python proc.py module: launch the game, find
/// its UnrealWindow, auto-click intro screens, and close it gracefully.
/// </summary>
public static class GameProcessService
{
    private const uint WM_CLOSE = 0x0010;
    private const uint WM_LBUTTONDOWN = 0x0201;
    private const uint WM_LBUTTONUP = 0x0202;
    private const uint MK_LBUTTON = 0x0001;

    private static readonly string[] ErrorTitlePatterns =
    {
        "fatal error", "lowlevelfatalerror", "assertion failed", "unreal engine",
        "crash reporter", "stopped working", "has crashed", "ue4-", "ue5-",
    };

    public static IReadOnlyList<int> FindGameProcessIds(string exePath)
    {
        var targetName = Path.GetFileNameWithoutExtension(exePath);
        var target = NormalizePath(exePath);
        var ids = new List<int>();
        foreach (var process in Process.GetProcesses())
        {
            try
            {
                // Match by process name first: this works across bitness (an
                // x86 app inspecting a x64 game), which MainModule cannot.
                if (string.Equals(
                    process.ProcessName, targetName, StringComparison.OrdinalIgnoreCase))
                {
                    ids.Add(process.Id);
                    continue;
                }
                // Fallback: compare full executable path when accessible.
                var fileName = process.MainModule?.FileName;
                if (!string.IsNullOrEmpty(fileName) &&
                    string.Equals(NormalizePath(fileName), target, StringComparison.OrdinalIgnoreCase))
                {
                    ids.Add(process.Id);
                }
            }
            catch (InvalidOperationException)
            { }
            catch (System.ComponentModel.Win32Exception)
            { }
            finally
            {
                process.Dispose();
            }
        }
        return ids;
    }

    public static Process? LaunchGame(string exePath, string? logPath, string extraArgs = "")
    {
        var startInfo = new ProcessStartInfo(exePath)
        {
            WorkingDirectory = Path.GetDirectoryName(exePath) ?? string.Empty,
            UseShellExecute = false,
        };
        if (!string.IsNullOrEmpty(logPath))
        {
            startInfo.ArgumentList.Add($"-abslog={logPath}");
        }
        if (!string.IsNullOrWhiteSpace(extraArgs))
        {
            foreach (var arg in extraArgs.Split(' ', StringSplitOptions.RemoveEmptyEntries))
            {
                startInfo.ArgumentList.Add(arg);
            }
        }

        try
        {
            return Process.Start(startInfo);
        }
        catch
        {
            return null;
        }
    }

    public static IReadOnlyList<(nint Hwnd, string Title, string Class)> FindGameMainWindows(
        IReadOnlyCollection<int> pids)
    {
        var pidSet = pids.ToHashSet();
        var result = new List<(nint, string, string)>();
        foreach (var (hwnd, title, cls) in EnumerateVisibleWindows())
        {
            if (!pidSet.Contains(GetWindowPid(hwnd)))
            {
                continue;
            }
            var lowerClass = cls.ToLowerInvariant();
            if (lowerClass == "unrealwindow" ||
                (title.Contains("ready or not", StringComparison.OrdinalIgnoreCase) &&
                 !lowerClass.Equals("consolewindowclass")))
            {
                result.Add((hwnd, title, cls));
            }
        }
        return result;
    }

    public static void ClickWindow(nint hwnd)
    {
        if (!GetClientRect(hwnd, out var rect))
        {
            return;
        }
        var x = (rect.Left + rect.Right) / 2;
        var y = (rect.Top + rect.Bottom) / 2;
        var lparam = (y << 16) | (x & 0xFFFF);
        PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam);
        PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam);
    }

    public static int PostCloseWindows(IReadOnlyCollection<int> pids)
    {
        var pidSet = pids.ToHashSet();
        var count = 0;
        foreach (var (hwnd, _, _) in EnumerateVisibleWindows())
        {
            if (pidSet.Contains(GetWindowPid(hwnd)))
            {
                PostMessageW(hwnd, WM_CLOSE, 0, 0);
                count++;
            }
        }
        return count;
    }

    public static void GracefulClose(IReadOnlyCollection<int> pids, double timeoutSeconds = 20)
    {
        if (pids.Count == 0)
        {
            return;
        }
        PostCloseWindows(pids);
        var deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
        while (DateTime.UtcNow < deadline)
        {
            if (!pids.Any(ProcessAlive))
            {
                return;
            }
            Thread.Sleep(250);
        }

        foreach (var pid in pids)
        {
            try { Process.GetProcessById(pid).Kill(); }
            catch { /* already gone */ }
        }
    }

    public static IReadOnlyList<(string Title, string Class)> FindErrorWindows(
        IReadOnlyList<string> ignoreTitles)
    {
        var result = new List<(string, string)>();
        foreach (var (_, title, cls) in EnumerateVisibleWindows())
        {
            var lowered = title.ToLowerInvariant();
            if (ignoreTitles.Any(ignore => lowered.Contains(ignore, StringComparison.OrdinalIgnoreCase)))
            {
                continue;
            }
            if (ErrorTitlePatterns.Any(pattern => lowered.Contains(pattern)))
            {
                result.Add((title, cls));
            }
        }
        return result;
    }

    public static bool IsSteamRunning()
    {
        foreach (var process in Process.GetProcessesByName("steam"))
        {
            process.Dispose();
            return true;
        }
        return false;
    }

    public static double? SampleTotalCpuMs(Process process)
    {
        try
        {
            process.Refresh();
            return process.TotalProcessorTime.TotalMilliseconds;
        }
        catch
        {
            return null;
        }
    }

    private static bool ProcessAlive(int pid)
    {
        try
        {
            using var process = Process.GetProcessById(pid);
            return !process.HasExited;
        }
        catch
        {
            return false;
        }
    }

    private static IEnumerable<(nint Hwnd, string Title, string Class)> EnumerateVisibleWindows()
    {
        var results = new List<(nint, string, string)>();
        EnumWindows((hwnd, _) =>
        {
            if (!IsWindowVisible(hwnd))
            {
                return true;
            }
            var titleLength = GetWindowTextLengthW(hwnd);
            if (titleLength <= 0)
            {
                return true;
            }
            var title = new char[titleLength + 1];
            GetWindowTextW(hwnd, title, title.Length);
            var cls = new char[256];
            GetClassNameW(hwnd, cls, cls.Length);
            results.Add((hwnd, new string(title).TrimEnd('\0'), new string(cls).TrimEnd('\0')));
            return true;
        }, 0);
        return results;
    }

    private static int GetWindowPid(nint hwnd)
    {
        GetWindowThreadProcessId(hwnd, out var pid);
        return (int)pid;
    }

    private static string NormalizePath(string path) =>
        Path.GetFullPath(path).TrimEnd('\\').ToLowerInvariant();

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT
    {
        public int Left, Top, Right, Bottom;
    }

    private delegate bool EnumWindowsProc(nint hwnd, nint lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc callback, nint lParam);
    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(nint hwnd);
    [DllImport("user32.dll")]
    private static extern int GetWindowTextLengthW(nint hwnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowTextW(nint hwnd, char[] lpString, int nMaxCount);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassNameW(nint hwnd, char[] lpClassName, int nMaxCount);
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint hwnd, out uint processId);
    [DllImport("user32.dll")]
    private static extern bool GetClientRect(nint hwnd, out RECT rect);
    [DllImport("user32.dll")]
    private static extern bool PostMessageW(nint hwnd, uint msg, nuint wParam, nint lParam);
}
