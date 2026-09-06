using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class AdvancedPage : Page, ILocalizablePage
{
    public AdvancedPage()
    {
        InitializeComponent();
        ApplyLanguage();
        LoadSettings();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Advanced");
        PageBodyText.Text = Localizer.T("Page.Advanced.Body");
        GameSectionText.Text = Localizer.T("Settings.Game");
        ToolsSectionText.Text = Localizer.T("Settings.Tools");
        TimingSectionText.Text = Localizer.T("Settings.Timing");
        StorageSectionText.Text = Localizer.T("Settings.Storage");
        BtnSave.Content = Localizer.T("Settings.Save");
    }

    private void LoadSettings()
    {
        var cfg = AppSettings.Current;
        GameRootBox.Text = cfg.GameRoot;
        ExePathBox.Text = cfg.ExePath;
        ExtraArgsBox.Text = cfg.ExtraArgs;
        RepakBox.Text = cfg.RepakExe;
        DotnetBox.Text = cfg.DotnetExe;
        UAssetCliBox.Text = cfg.UAssetCliDll;
        StableBox.Text = cfg.StableSeconds.ToString();
        StartupBox.Text = cfg.StartupTimeoutSeconds.ToString();
        MenuHoldBox.Text = cfg.MenuHoldSeconds.ToString();
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
        cfg.RepakExe = RepakBox.Text.Trim();
        cfg.DotnetExe = DotnetBox.Text.Trim();
        cfg.UAssetCliDll = UAssetCliBox.Text.Trim();
        if (double.TryParse(StableBox.Text, out var stable)) cfg.StableSeconds = stable;
        if (double.TryParse(StartupBox.Text, out var startup)) cfg.StartupTimeoutSeconds = startup;
        if (double.TryParse(MenuHoldBox.Text, out var menuHold)) cfg.MenuHoldSeconds = menuHold;
        cfg.ReportDir = ReportDirBox.Text.Trim();
        cfg.BackupDir = BackupDirBox.Text.Trim();
        cfg.QuarantineDir = QuarantineDirBox.Text.Trim();
        AppSettings.Save();
        StatusText.Text = Localizer.T("Settings.Saved");
    }
}
