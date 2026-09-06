using System.Diagnostics;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;
using RoNCT.Core.Deployment;

namespace RoNCT.App.Pages;

public sealed partial class BackupPage : Page, ILocalizablePage
{
    public BackupPage()
    {
        InitializeComponent();
        ApplyLanguage();
        RefreshBackupList();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Backup");
        PageBodyText.Text = Localizer.T("Page.Backup.Body");
        BtnCreateBackup.Content = Localizer.T("Backup.Create");
        BtnRestore.Content = Localizer.T("Backup.Restore");
        BtnOpenBackup.Content = Localizer.T("Backup.Open");
        BackupListHeader.Text = Localizer.T("Backup.ListHeader");
        BackupPathText.Text = Localizer.T("Backup.Path") + " " + BackupDirectory();
    }

    private static string BackupDirectory()
    {
        var configured = AppSettings.Current.BackupDir;
        return !string.IsNullOrEmpty(configured)
            ? configured
            : Path.Combine(AppSettings.DataDirectory, "backup");
    }

    private static string GameModDirectory()
    {
        if (!string.IsNullOrEmpty(AppSettings.Current.ModFolder) &&
            Directory.Exists(AppSettings.Current.ModFolder))
        {
            return AppSettings.Current.ModFolder;
        }
        if (!string.IsNullOrEmpty(AppSettings.Current.GameRoot))
        {
            var candidate = Path.Combine(
                AppSettings.Current.GameRoot, "ReadyOrNot", "Content", "Paks");
            if (Directory.Exists(candidate))
            {
                return candidate;
            }
        }
        return @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks";
    }

    private void BtnCreateBackup_Click(object sender, RoutedEventArgs e)
    {
        var backup = BackupDirectory();
        try
        {
            var (_, manifestPath) = BackupService.CreateBackup(
                GameModDirectory(),
                backup,
                backupEnabled: true,
                maxFileBytes: AppSettings.Current.BackupMaxFileMb * 1024 * 1024,
                maxTotalBytes: AppSettings.Current.BackupMaxTotalMb * 1024 * 1024);
            StatusText.Text = Localizer.T("Backup.Created") + " " + manifestPath;
        }
        catch (Exception exc)
        {
            StatusText.Text = exc.Message;
        }
        RefreshBackupList();
    }

    private void BtnRestore_Click(object sender, RoutedEventArgs e)
    {
        var backup = BackupDirectory();
        if (!File.Exists(Path.Combine(backup, BackupService.ManifestName)))
        {
            StatusText.Text = Localizer.T("Backup.NoBackup");
            return;
        }
        try
        {
            var (restored, removed) = BackupService.RestoreBackup(
                backup, GameModDirectory(), removeNew: true);
            StatusText.Text = string.Format(
                Localizer.T("Backup.Restored"), restored.Count, removed.Count);
        }
        catch (Exception exc)
        {
            StatusText.Text = exc.Message;
        }
    }

    private void BtnOpenBackup_Click(object sender, RoutedEventArgs e)
    {
        var dir = BackupDirectory();
        Directory.CreateDirectory(dir);
        Process.Start(new ProcessStartInfo("explorer.exe", dir) { UseShellExecute = true });
    }

    private void RefreshBackupList()
    {
        BackupList.Items.Clear();
        var dir = BackupDirectory();
        if (!Directory.Exists(dir))
        {
            return;
        }

        if (File.Exists(Path.Combine(dir, BackupService.ManifestName)))
        {
            BackupList.Items.Add($"manifest.json  ({Localizer.T("Backup.Manifest")})");
        }
        foreach (var pak in Directory.EnumerateFiles(dir, "*.pak"))
        {
            var info = new FileInfo(pak);
            BackupList.Items.Add($"{info.Name}  ({info.Length / 1024} KB)");
        }
    }
}
