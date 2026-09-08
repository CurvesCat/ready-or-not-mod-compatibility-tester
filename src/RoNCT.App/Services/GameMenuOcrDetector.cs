using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.WindowsRuntime;
using Windows.Globalization;
using Windows.Graphics.Imaging;
using Windows.Media.Ocr;

namespace RoNCT.App.Services;

public sealed record OcrScanResult(
    bool MenuLikely,
    IReadOnlyList<string> Lines);

/// <summary>
/// Ready or Not ships without a usable UE log on some machines, and the menu
/// keeps CPU high, so menu detection falls back to OCR of the game window.
/// The detector only accelerates the result: when OCR is unavailable or sees
/// nothing, callers keep their existing stable-window fallback.
/// </summary>
public static class GameMenuOcrDetector
{
    private static readonly string[] StrongMenuPhrases =
    {
        "main menu", "campaign", "command", "continue", "loadout",
        "deployment", "officer", "player limit editor", "max connections",
        "max players", "set max", "simple mod menu", "singleplayer",
        "multiplayer",
    };

    private static OcrEngine? _engine;

    public static bool IsAvailable
    {
        get
        {
            _ = EnsureEngine();
            return _engine is not null;
        }
    }

    public static void WarmUp(nint hwnd)
    {
        try
        {
            using var bitmap = CaptureWindow(hwnd);
        }
        catch
        {
            // best effort; OCR will retry on its normal schedule
        }
    }

    public static async Task<OcrScanResult> ScanAsync(nint hwnd)
    {
        var engine = EnsureEngine();
        if (engine is null || hwnd == 0)
        {
            return new OcrScanResult(false, Array.Empty<string>());
        }

        using var bitmap = CaptureWindow(hwnd);
        return bitmap is null
            ? new OcrScanResult(false, Array.Empty<string>())
            : await ScanBitmapAsync(engine, bitmap);
    }

    private static async Task<OcrScanResult> ScanBitmapAsync(
        OcrEngine engine,
        Bitmap bitmap)
    {
        try
        {
            using var memory = new MemoryStream();
            bitmap.Save(memory, ImageFormat.Png);
            memory.Position = 0;
            using var stream = memory.AsRandomAccessStream();
            var decoder = await BitmapDecoder.CreateAsync(stream);
            var software = await decoder.GetSoftwareBitmapAsync();
            using (software)
            {
                var ocr = await engine.RecognizeAsync(software);
                var lines = ocr.Lines
                    .Select(line => line.Text.Trim())
                    .Where(line => line.Length > 0)
                    .ToArray();
                return new OcrScanResult(LooksLikeMenu(lines), lines);
            }
        }
        catch
        {
            return new OcrScanResult(false, Array.Empty<string>());
        }
    }

    public static OcrScanResult ScanBlocking(nint hwnd) =>
        Task.Run(() => ScanAsync(hwnd)).GetAwaiter().GetResult();

    private static bool LooksLikeMenu(IReadOnlyList<string> lines)
    {
        var meaningful = lines
            .Count(line => line.Any(char.IsLetter));
        if (meaningful >= 4)
        {
            return true;
        }

        var compact = string.Concat(lines)
            .ToLowerInvariant()
            .Where(char.IsLetterOrDigit)
            .ToArray();
        var text = new string(compact);
        return StrongMenuPhrases.Any(
            phrase => text.Contains(phrase, StringComparison.Ordinal));
    }

    private static Bitmap? CaptureWindow(nint hwnd)
    {
        if (!GetWindowRect(hwnd, out var rect) ||
            rect.Right <= rect.Left ||
            rect.Bottom <= rect.Top)
        {
            return null;
        }

        var width = rect.Right - rect.Left;
        var height = rect.Bottom - rect.Top;
        if (width <= 0 || height <= 0 || width > 8000 || height > 8000)
        {
            return null;
        }

        var bitmap = new Bitmap(width, height);
        try
        {
            using var graphics = Graphics.FromImage(bitmap);
            var hdc = graphics.GetHdc();
            try
            {
                PrintWindow(hwnd, hdc, 2);
            }
            finally
            {
                graphics.ReleaseHdc(hdc);
            }
            return bitmap;
        }
        catch
        {
            bitmap.Dispose();
            return null;
        }
    }

    private static OcrEngine? EnsureEngine()
    {
        if (_engine is not null)
        {
            return _engine;
        }

        try
        {
            _engine = OcrEngine.TryCreateFromLanguage(new Language("en-US"));
        }
        catch
        {
            _engine = null;
        }
        _engine ??= OcrEngine.TryCreateFromUserProfileLanguages();
        return _engine;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(nint hwnd, out RECT rect);

    [DllImport("user32.dll")]
    private static extern bool PrintWindow(nint hwnd, nint hdc, uint flags);

}
