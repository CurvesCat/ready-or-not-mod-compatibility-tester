using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class AdvancedPage : Page, ILocalizablePage
{
    private MainWindow? _window;
    private bool _calibrating;

    private static readonly string KnownGameRoot =
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not";
    private static readonly string KnownExe =
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Binaries\Win64\ReadyOrNotSteam-Win64-Shipping.exe";

    public AdvancedPage()
    {
        InitializeComponent();
        LoadSettings();
        ApplyLanguage();
    }

    public void AttachWindow(MainWindow window) =>
        _window = window;

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Advanced");
        PageBodyText.Text = Localizer.T("Page.Advanced.Body");
        GameSectionText.Text = Localizer.T("Settings.Game");
        TimingSectionText.Text = Localizer.T("Settings.Timing");
        ToolsSectionText.Text = Localizer.T("Settings.Tools");
        BackupSectionText.Text = Localizer.T("Settings.Backup");
        BtnCalibrateNow.Content = Localizer.T("Settings.CalibrateNow");
        BtnSave.Content = Localizer.T("Settings.Save");
        GameRootBox.Header = Localizer.T("Settings.GameRoot");
        ExePathBox.Header = Localizer.T("Settings.ExePath");
        ExtraArgsBox.Header = Localizer.T("Settings.ExtraArgs");
        CloseRunningBox.Content = Localizer.T("Settings.CloseRunning");
        AutoCalibrateBox.Content = Localizer.T("Settings.AutoCalibrate");
        StableBox.Header = Localizer.T("Settings.StableSeconds");
        StartupBox.Header = Localizer.T("Settings.StartupTimeout");
        MenuHoldBox.Header = Localizer.T("Settings.MenuHoldSeconds");
        RepakBox.Header = Localizer.T("Settings.Repak");
        DotnetBox.Header = Localizer.T("Settings.Dotnet");
        UAssetCliBox.Header = Localizer.T("Settings.UAssetCli");
        EngineBox.Header = Localizer.T("Settings.Engine");
        AssetLimitBox.Header = Localizer.T("Settings.AssetLimit");
        WorkersBox.Header = Localizer.T("Settings.Workers");
        AnalyzeDepsBox.Content = Localizer.T("Settings.AnalyzeDeps");
        BackupEnabledBox.Content = Localizer.T("Settings.BackupEnabled");
        BackupMaxFileBox.Header = Localizer.T("Settings.BackupMaxFile");
        BackupMaxTotalBox.Header = Localizer.T("Settings.BackupMaxTotal");
        ReportDirBox.Header = Localizer.T("Settings.ReportDir");
        BackupDirBox.Header = Localizer.T("Settings.BackupDir");
        QuarantineDirBox.Header = Localizer.T("Settings.QuarantineDir");
        SourceCombo.Header = Localizer.T("Settings.Source");
        DispositionCombo.Header = Localizer.T("Settings.Disposition");
        WarmupBox.Content = Localizer.T("Settings.Warmup");
        RefreshSourceCombo();
        RefreshDispositionCombo();
    }

    private void RefreshSourceCombo()
    {
        var index = AppSettings.Current.Source == "installed" ? 1 : 0;
        SourceCombo.Items.Clear();
        SourceCombo.Items.Add(Localizer.T("Settings.Source.Folder"));
        SourceCombo.Items.Add(Localizer.T("Settings.Source.Installed"));
        SourceCombo.SelectedIndex = index;
    }

    private void RefreshDispositionCombo()
    {
        var index = AppSettings.Current.Disposition == "delete" ? 1 : 0;
        DispositionCombo.Items.Clear();
        DispositionCombo.Items.Add(Localizer.T("Settings.Disposition.Quarantine"));
        DispositionCombo.Items.Add(Localizer.T("Settings.Disposition.Delete"));
        DispositionCombo.SelectedIndex = index;
    }

    private void LoadSettings()
    {
        var cfg = AppSettings.Current;
        GameRootBox.Text = !string.IsNullOrEmpty(cfg.GameRoot)
            ? cfg.GameRoot
            : (Directory.Exists(KnownGameRoot) ? KnownGameRoot : string.Empty);
        ExePathBox.Text = !string.IsNullOrEmpty(cfg.ExePath)
            ? cfg.ExePath
            : (File.Exists(KnownExe) ? KnownExe : string.Empty);
        ExtraArgsBox.Text = cfg.ExtraArgs;
        CloseRunningBox.IsChecked = cfg.CloseRunning;
        AutoCalibrateBox.IsChecked = cfg.AutoCalibrate;
        StableBox.Text = cfg.StableSeconds.ToString();
        StartupBox.Text = cfg.StartupTimeoutSeconds.ToString();
        MenuHoldBox.Text = cfg.MenuHoldSeconds.ToString();
        RepakBox.Text = ResolveTool(cfg.RepakExe, "repak", "repak.exe");
        DotnetBox.Text = ResolveTool(cfg.DotnetExe, "dotnet", "dotnet.exe");
        UAssetCliBox.Text = ResolveTool(
            cfg.UAssetCliDll, "uassetcli", "UAssetCLI.dll");
        EngineBox.Text = string.IsNullOrEmpty(cfg.Engine) ? "VER_UE5_4" : cfg.Engine;
        AssetLimitBox.Text = cfg.AssetLimit.ToString();
        WorkersBox.Text = cfg.Workers.ToString();
        AnalyzeDepsBox.IsChecked = cfg.AnalyzeDeps;
        BackupEnabledBox.IsChecked = cfg.BackupEnabled;
        BackupMaxFileBox.Text = cfg.BackupMaxFileMb.ToString();
        BackupMaxTotalBox.Text = cfg.BackupMaxTotalMb.ToString();
        ReportDirBox.Text = string.IsNullOrEmpty(cfg.ReportDir)
            ? Path.Combine(AppSettings.DataDirectory, "reports")
            : cfg.ReportDir;
        BackupDirBox.Text = string.IsNullOrEmpty(cfg.BackupDir)
            ? Path.Combine(AppSettings.DataDirectory, "backup")
            : cfg.BackupDir;
        QuarantineDirBox.Text = string.IsNullOrEmpty(cfg.QuarantineDir)
            ? Path.Combine(AppSettings.DataDirectory, "quarantine")
            : cfg.QuarantineDir;
    }

    private static string ResolveTool(string configured, params string[] parts)
    {
        if (!string.IsNullOrEmpty(configured))
        {
            return configured;
        }
        var path = Path.Combine(
            AppSettings.DataDirectory, "tools", Path.Combine(parts));
        return File.Exists(path) ? path : string.Empty;
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        PersistEdits();
        AppLog.UserAction("settings_saved");
        StatusText.Text = Localizer.T("Settings.Saved");
    }

    private void PersistEdits()
    {
        var cfg = AppSettings.Current;
        cfg.GameRoot = GameRootBox.Text.Trim();
        cfg.ExePath = ExePathBox.Text.Trim();
        cfg.ExtraArgs = ExtraArgsBox.Text.Trim();
        cfg.CloseRunning = CloseRunningBox.IsChecked == true;
        cfg.AutoCalibrate = AutoCalibrateBox.IsChecked == true;
        cfg.Source = SourceCombo.SelectedIndex == 1 ? "installed" : "folder";
        cfg.Disposition = DispositionCombo.SelectedIndex == 1 ? "delete" : "quarantine";
        cfg.Warmup = WarmupBox.IsChecked == true;
        if (double.TryParse(StableBox.Text, out var v1)) cfg.StableSeconds = v1;
        if (double.TryParse(StartupBox.Text, out var v2)) cfg.StartupTimeoutSeconds = v2;
        if (double.TryParse(MenuHoldBox.Text, out var v3)) cfg.MenuHoldSeconds = v3;
        cfg.RepakExe = RepakBox.Text.Trim();
        cfg.DotnetExe = DotnetBox.Text.Trim();
        cfg.UAssetCliDll = UAssetCliBox.Text.Trim();
        cfg.Engine = string.IsNullOrEmpty(EngineBox.Text.Trim()) ? "VER_UE5_4" : EngineBox.Text.Trim();
        if (int.TryParse(AssetLimitBox.Text, out var v4)) cfg.AssetLimit = v4;
        if (int.TryParse(WorkersBox.Text, out var v5)) cfg.Workers = v5;
        cfg.AnalyzeDeps = AnalyzeDepsBox.IsChecked == true;
        cfg.BackupEnabled = BackupEnabledBox.IsChecked == true;
        if (long.TryParse(BackupMaxFileBox.Text, out var v6)) cfg.BackupMaxFileMb = v6;
        if (long.TryParse(BackupMaxTotalBox.Text, out var v7)) cfg.BackupMaxTotalMb = v7;
        cfg.ReportDir = ReportDirBox.Text.Trim();
        cfg.BackupDir = BackupDirBox.Text.Trim();
        cfg.QuarantineDir = QuarantineDirBox.Text.Trim();
        AppSettings.Save();
    }

    private async void BtnCalibrateNow_Click(object sender, RoutedEventArgs e)
    {
        if (_calibrating)
        {
            return;
        }

        PersistEdits();
        var cfg = AppSettings.Current;
        var exe = !string.IsNullOrEmpty(cfg.ExePath)
            ? cfg.ExePath
            : (File.Exists(KnownExe) ? KnownExe : string.Empty);
        if (string.IsNullOrEmpty(exe))
        {
            StatusText.Text = Localizer.T("Settings.CalibrateNoExe");
            return;
        }

        AppLog.UserAction("calibrate_now");
        _calibrating = true;
        BtnCalibrateNow.IsEnabled = false;
        CalibrateProgress.Visibility = Visibility.Visible;
        StatusText.Text = Localizer.T("Settings.Calibrating");
        var queue = _window?.DispatcherQueue;
        var logDir = Path.Combine(AppSettings.DataDirectory, "logs");

        try
        {
            var cal = await Task.Run(() => CalibrationService.Run(
                exe,
                cfg.ExtraArgs,
                logDir,
                cfg.StartupTimeoutSeconds,
                120,
                message => queue?.TryEnqueue(() => StatusText.Text = message)));

            var windowSeconds = cal.WindowSeconds ?? 0;
            var suggestedStartup = Math.Min(
                900,
                Math.Max(60, (int)Math.Ceiling(windowSeconds * 1.8) + 30));
            suggestedStartup = Math.Max(
                suggestedStartup, (int)Math.Ceiling(cfg.StartupTimeoutSeconds));

            cfg.StableSeconds = cal.SuggestedStable;
            cfg.StartupTimeoutSeconds = suggestedStartup;
            AppSettings.Save();

            StableBox.Text = cfg.StableSeconds.ToString();
            StartupBox.Text = cfg.StartupTimeoutSeconds.ToString();
            StatusText.Text = string.Format(
                Localizer.T("Settings.CalibrateDone"),
                cal.WindowSeconds.HasValue
                    ? cal.WindowSeconds.Value.ToString("0.0") + "s"
                    : Localizer.T("Settings.CalibrateUnknown"),
                cal.MenuSeconds.HasValue
                    ? cal.MenuSeconds.Value.ToString("0.0") + "s"
                    : Localizer.T("Settings.CalibrateUnknown"),
                cfg.StableSeconds.ToString("0"),
                cfg.StartupTimeoutSeconds.ToString("0"));
        }
        catch (Exception exc)
        {
            AppLog.Error("AdvancedPage calibration failed: " + exc);
            StatusText.Text = string.Format(
                Localizer.T("Settings.CalibrateFailed"), exc.Message);
        }
        finally
        {
            _calibrating = false;
            BtnCalibrateNow.IsEnabled = true;
            CalibrateProgress.Visibility = Visibility.Collapsed;
        }
    }

    private async void BtnBrowseGameRoot_Click(object sender, RoutedEventArgs e) =>
        await BrowseFolderAsync(GameRootBox);
    private async void BtnBrowseExe_Click(object sender, RoutedEventArgs e) =>
        await BrowseFileAsync(ExePathBox, ".exe");
    private async void BtnBrowseRepak_Click(object sender, RoutedEventArgs e) =>
        await BrowseFileAsync(RepakBox, ".exe");
    private async void BtnBrowseDotnet_Click(object sender, RoutedEventArgs e) =>
        await BrowseFileAsync(DotnetBox, ".exe");
    private async void BtnBrowseUAssetCli_Click(object sender, RoutedEventArgs e) =>
        await BrowseFileAsync(UAssetCliBox, ".dll");
    private async void BtnBrowseReportDir_Click(object sender, RoutedEventArgs e) =>
        await BrowseFolderAsync(ReportDirBox);
    private async void BtnBrowseBackupDir_Click(object sender, RoutedEventArgs e) =>
        await BrowseFolderAsync(BackupDirBox);
    private async void BtnBrowseQuarantineDir_Click(object sender, RoutedEventArgs e) =>
        await BrowseFolderAsync(QuarantineDirBox);

    private async Task BrowseFolderAsync(TextBox box)
    {
        if (_window is null)
        {
            return;
        }
        var path = await WindowsPicker.PickFolderAsync(
            _window, StartDirectoryFor(box.Text));
        if (!string.IsNullOrEmpty(path))
        {
            box.Text = path;
        }
    }

    private async Task BrowseFileAsync(TextBox box, params string[] extensions)
    {
        if (_window is null)
        {
            return;
        }
        var path = await WindowsPicker.PickSingleFileAsync(
            _window, extensions, StartDirectoryFor(box.Text));
        if (!string.IsNullOrEmpty(path))
        {
            box.Text = path;
        }
    }

    /// <summary>
    /// Reuses the location already typed into the settings box. A directory is
    /// used as-is; a file path opens at its parent so users do not have to
    /// navigate back from Documents every time.
    /// </summary>
    private static string? StartDirectoryFor(string currentValue)
    {
        if (string.IsNullOrWhiteSpace(currentValue))
        {
            return null;
        }

        var trimmed = currentValue.Trim().Trim('"');
        if (Directory.Exists(trimmed))
        {
            return trimmed;
        }

        if (File.Exists(trimmed))
        {
            var parent = Path.GetDirectoryName(trimmed);
            return string.IsNullOrEmpty(parent) ? null : parent;
        }

        return null;
    }
}
