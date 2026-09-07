using System.Diagnostics;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class QuarantinePage : Page, ILocalizablePage
{
    public QuarantinePage()
    {
        InitializeComponent();
        ApplyLanguage();
        RefreshList();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Quarantine");
        BtnOpenQuarantine.Content = Localizer.T("Quarantine.Open");
        BtnDeleteSelected.Content = Localizer.T("Quarantine.Delete");
        BtnEmpty.Content = Localizer.T("Quarantine.Empty");
        QuarantinePathText.Text = Localizer.T("Quarantine.Path") + " " + QuarantineDirectory();
    }

    private static string QuarantineDirectory()
    {
        var configured = AppSettings.Current.QuarantineDir;
        return !string.IsNullOrEmpty(configured)
            ? configured
            : Path.Combine(AppSettings.DataDirectory, "quarantine");
    }

    private void BtnOpenQuarantine_Click(object sender, RoutedEventArgs e)
    {
        var dir = QuarantineDirectory();
        Directory.CreateDirectory(dir);
        AppLog.Log("USER_ACTION: open quarantine folder");
        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = "explorer.exe",
                UseShellExecute = true,
                Arguments = $"\"{dir}\"",
            });
        }
        catch (Exception exc)
        {
            AppLog.Log($"QuarantinePage: open failed: {exc.Message}");
            StatusText.Text = exc.Message;
        }
    }

    private void BtnDeleteSelected_Click(object sender, RoutedEventArgs e)
    {
        var names = QuarantineList.SelectedItems.Cast<string>().ToList();
        if (names.Count == 0)
        {
            StatusText.Text = Localizer.T("Quarantine.NoneSelected");
            return;
        }

        var deleted = 0;
        foreach (var name in names)
        {
            try
            {
                var path = Path.Combine(QuarantineDirectory(), name);
                if (File.Exists(path))
                {
                    File.Delete(path);
                    deleted++;
                }
            }
            catch (Exception exc)
            {
                AppLog.Log($"QuarantinePage: delete {name} failed: {exc.Message}");
            }
        }
        AppLog.Log($"USER_ACTION: delete selected quarantine items ({deleted}/{names.Count})");
        StatusText.Text = string.Format(Localizer.T("Quarantine.Deleted"), deleted);
        RefreshList();
    }

    private void BtnEmpty_Click(object sender, RoutedEventArgs e)
    {
        var count = 0;
        foreach (var name in QuarantineList.Items.Cast<string>().ToList())
        {
            try
            {
                var path = Path.Combine(QuarantineDirectory(), name);
                if (File.Exists(path))
                {
                    File.Delete(path);
                    count++;
                }
            }
            catch (Exception exc)
            {
                AppLog.Log($"QuarantinePage: empty failed for {name}: {exc.Message}");
            }
        }
        AppLog.Log($"USER_ACTION: empty quarantine ({count} deleted)");
        StatusText.Text = string.Format(Localizer.T("Quarantine.Deleted"), count);
        RefreshList();
    }

    private void RefreshList()
    {
        QuarantineList.Items.Clear();
        var dir = QuarantineDirectory();
        if (Directory.Exists(dir))
        {
            foreach (var file in Directory.EnumerateFiles(dir))
            {
                QuarantineList.Items.Add(Path.GetFileName(file));
            }
        }
    }
}
