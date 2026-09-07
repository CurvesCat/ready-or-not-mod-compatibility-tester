using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Data;
using Microsoft.UI.Xaml.Input;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Navigation;
using RoNCT.App.Services;

// To learn more about WinUI, the WinUI project structure,
// and more about our project templates, see: http://aka.ms/winui-project-info.

namespace RoNCT.App;

/// <summary>
/// Provides application-specific behavior to supplement the default Application class.
/// </summary>
public partial class App : Application
{
    private Window? _window;
    
    /// <summary>
    /// Initializes the singleton application object.  This is the first line of authored code
    /// executed, and as such is the logical equivalent of main() or WinMain().
    /// </summary>
    public App()
    {
        InitializeComponent();
    }

    /// <summary>
    /// Invoked when the application is launched.
    /// </summary>
    /// <param name="args">Details about the launch request and process.</param>
    protected override void OnLaunched(Microsoft.UI.Xaml.LaunchActivatedEventArgs args)
    {
        var cmdArgs = Environment.GetCommandLineArgs();
        if (cmdArgs.Contains("--selfcal", StringComparer.OrdinalIgnoreCase))
        {
            RunSelfCalibration();
            Environment.Exit(0);
            return;
        }

        Localizer.SetLanguage(AppSettings.Current.Language);
        _window = new MainWindow();
        _window.Activate();
    }

    private static void RunSelfCalibration()
    {
        var knownExe =
            @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Binaries\Win64\ReadyOrNotSteam-Win64-Shipping.exe";
        var exe = !string.IsNullOrEmpty(AppSettings.Current.ExePath)
            ? AppSettings.Current.ExePath
            : (File.Exists(knownExe) ? knownExe : string.Empty);
        var logDir = Path.Combine(AppSettings.DataDirectory, "logs");
        Directory.CreateDirectory(logDir);
        var outPath = Path.Combine(logDir, "selfcal.txt");

        try
        {
            var cal = CalibrationService.Run(
                exe,
                AppSettings.Current.ExtraArgs,
                logDir,
                180,
                120,
                AppLog.Log);
            File.WriteAllText(
                outPath,
                $"window={cal.WindowSeconds:0.0} menu={cal.MenuSeconds:0.0} stable={cal.SuggestedStable:0}");
            AppLog.Log($"selfcal done: window={cal.WindowSeconds:0.0} menu={cal.MenuSeconds:0.0} stable={cal.SuggestedStable:0}");
        }
        catch (Exception exc)
        {
            File.WriteAllText(outPath, "ERROR: " + exc.Message);
            AppLog.Log("selfcal error: " + exc);
        }
    }
}
