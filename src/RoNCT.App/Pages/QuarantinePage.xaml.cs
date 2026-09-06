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
        PageBodyText.Text = Localizer.T("Page.Quarantine.Body");
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
        Process.Start(new ProcessStartInfo("explorer.exe", dir) { UseShellExecute = true });
    }

    private void BtnDeleteSelected_Click(object sender, RoutedEventArgs e)
    {
        var names = QuarantineList.SelectedItems.Cast<string>().ToList();
        foreach (var name in names)
        {
            try
            {
                var path = Path.Combine(QuarantineDirectory(), name);
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch (IOException)
            {
                // keep listing
            }
        }
        StatusText.Text = string.Format(Localizer.T("Quarantine.Deleted"), names.Count);
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
            catch (IOException)
            {
                // keep going
            }
        }
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
