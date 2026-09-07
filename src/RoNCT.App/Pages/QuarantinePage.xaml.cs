using System.Diagnostics;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class QuarantinePage : Page, ILocalizablePage
{
    private bool _dialogOpen;

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

    private async void BtnDeleteSelected_Click(object sender, RoutedEventArgs e)
    {
        var names = QuarantineList.SelectedItems.Cast<string>().ToList();
        if (names.Count == 0)
        {
            StatusText.Text = Localizer.T("Quarantine.NoneSelected");
            return;
        }

        if (!await ConfirmPermanentDeleteAsync(
                Localizer.T("Quarantine.DeleteSelectedTitle"),
                string.Format(Localizer.T("Quarantine.DeleteSelectedConfirm"), names.Count)))
        {
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

    private async void BtnEmpty_Click(object sender, RoutedEventArgs e)
    {
        var items = QuarantineList.Items.Cast<string>().ToList();
        if (items.Count == 0)
        {
            StatusText.Text = string.Format(Localizer.T("Quarantine.Deleted"), 0);
            return;
        }

        if (!await ConfirmPermanentDeleteAsync(
                Localizer.T("Quarantine.EmptyTitle"),
                string.Format(Localizer.T("Quarantine.EmptyConfirm"), items.Count)))
        {
            return;
        }

        var count = 0;
        foreach (var name in items)
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

    /// <summary>
    /// Quarantine files are the only remaining copies of rejected mods, so
    /// deleting them must always be confirmed by the user.
    /// </summary>
    private async Task<bool> ConfirmPermanentDeleteAsync(
        string title,
        string message)
    {
        if (_dialogOpen)
        {
            return false;
        }

        _dialogOpen = true;
        try
        {
            var dialog = new ContentDialog
            {
                Title = title,
                Content = message,
                PrimaryButtonText = Localizer.T("Quarantine.DeleteNow"),
                CloseButtonText = Localizer.T("Dialog.Cancel"),
                DefaultButton = ContentDialogButton.Close,
                XamlRoot = XamlRoot,
            };
            return await dialog.ShowAsync() == ContentDialogResult.Primary;
        }
        finally
        {
            _dialogOpen = false;
        }
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
