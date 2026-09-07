using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class AdvancedPage : Page, ILocalizablePage
{
    public AdvancedPage()
    {
        InitializeComponent();
        LoadSettings();
        ApplyLanguage();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Advanced");
        PageBodyText.Text = Localizer.T("Page.Advanced.Body");
        GameSectionText.Text = Localizer.T("Settings.Game");
        TimingSectionText.Text = Localizer.T("Settings.Timing");
        ToolsSectionText.Text = Localizer.T("Settings.Tools");
        BackupSectionText.Text = Localizer.T("Settings.Backup");
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
    }

    private void LoadSettings()
    {
        var cfg = AppSettings.Current;
        GameRootBox.Text = cfg.GameRoot;
        ExePathBox.Text = cfg.ExePath;
        ExtraArgsBox.Text = cfg.ExtraArgs;
        CloseRunningBox.IsChecked = cfg.CloseRunning;
        AutoCalibrateBox.IsChecked = cfg.AutoCalibrate;
        StableBox.Text = cfg.StableSeconds.ToString();
        StartupBox.Text = cfg.StartupTimeoutSeconds.ToString();
        MenuHoldBox.Text = cfg.MenuHoldSeconds.ToString();
        RepakBox.Text = cfg.RepakExe;
        DotnetBox.Text = cfg.DotnetExe;
        UAssetCliBox.Text = cfg.UAssetCliDll;
        EngineBox.Text = cfg.Engine;
        AssetLimitBox.Text = cfg.AssetLimit.ToString();
        WorkersBox.Text = cfg.Workers.ToString();
        AnalyzeDepsBox.IsChecked = cfg.AnalyzeDeps;
        BackupEnabledBox.IsChecked = cfg.BackupEnabled;
        BackupMaxFileBox.Text = cfg.BackupMaxFileMb.ToString();
        BackupMaxTotalBox.Text = cfg.BackupMaxTotalMb.ToString();
        ReportDirBox.Text = cfg.ReportDir;
        BackupDirBox.Text = cfg.BackupDir;
        QuarantineDirBox.Text = cfg.QuarantineDir;
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        var cfg = AppSettings.Current;
        cfg.GameRoot = GameRootBox.Text.Trim();
        cfg.ExePath = ExePathBox.Text.Trim();
        cfg.ExtraArgs = ExtraArgsBox.Text.Trim();
        cfg.CloseRunning = CloseRunningBox.IsChecked == true;
        cfg.AutoCalibrate = AutoCalibrateBox.IsChecked == true;
        if (double.TryParse(StableBox.Text, out var v1)) cfg.StableSeconds = v1;
        if (double.TryParse(StartupBox.Text, out var v2)) cfg.StartupTimeoutSeconds = v2;
        if (double.TryParse(MenuHoldBox.Text, out var v3)) cfg.MenuHoldSeconds = v3;
        cfg.RepakExe = RepakBox.Text.Trim();
        cfg.DotnetExe = DotnetBox.Text.Trim();
        cfg.UAssetCliDll = UAssetCliBox.Text.Trim();
        cfg.Engine = string.IsNullOrEmpty(EngineBox.Text.Trim())
            ? "VER_UE5_4"
            : EngineBox.Text.Trim();
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
        StatusText.Text = Localizer.T("Settings.Saved");
    }
}
