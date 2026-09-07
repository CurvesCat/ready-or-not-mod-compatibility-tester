using System.Diagnostics;
using Windows.ApplicationModel.DataTransfer;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class DebugPage : Page, ILocalizablePage
{
    public DebugPage()
    {
        InitializeComponent();
        ApplyLanguage();
        RefreshLog();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Debug");
        PageBodyText.Text = Localizer.T("Page.Debug.Body");
        BtnRefresh.Content = Localizer.T("Debug.Refresh");
        BtnCopyLog.Content = Localizer.T("Debug.CopyLog");
        BtnCopyDiagnostics.Content = Localizer.T("Debug.CopyDiagnostics");
        BtnOpenFolder.Content = Localizer.T("Debug.OpenFolder");
        LogPathText.Text = string.Format(
            Localizer.T("Debug.LogPath"), AppLog.LogFile);
    }

    private void BtnRefresh_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("debug_refresh");
        RefreshLog();
    }

    private void RefreshLog()
    {
        try
        {
            if (!File.Exists(AppLog.LogFile))
            {
                LogTextBox.Text = Localizer.T("Debug.NoLog");
                return;
            }

            var lines = File.ReadAllLines(AppLog.LogFile);
            var keep = Math.Min(lines.Length, 800);
            var tail = lines.Skip(lines.Length - keep);
            LogTextBox.Text = keep < lines.Length
                ? $"... ({lines.Length - keep} older lines hidden) ...\n{string.Join("\n", tail)}"
                : string.Join("\n", tail);
        }
        catch (Exception exc)
        {
            AppLog.Error("DebugPage refresh failed: " + exc);
            LogTextBox.Text = exc.Message;
        }
    }

    private async void BtnCopyLog_Click(object sender, RoutedEventArgs e)
    {
        if (!File.Exists(AppLog.LogFile))
        {
            StatusText.Text = Localizer.T("Debug.NoLog");
            return;
        }

        try
        {
            var package = new DataPackage();
            package.SetText(await File.ReadAllTextAsync(AppLog.LogFile));
            Clipboard.SetContent(package);
            StatusText.Text = Localizer.T("Debug.Copied");
        }
        catch (Exception exc)
        {
            AppLog.Error("DebugPage copy log failed: " + exc);
            StatusText.Text = exc.Message;
        }
    }

    private void BtnCopyDiagnostics_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var text = DiagnosticsService.Collect(AppSettings.Current);
            var package = new DataPackage();
            package.SetText(text);
            Clipboard.SetContent(package);
            StatusText.Text = Localizer.T("Debug.Copied");
        }
        catch (Exception exc)
        {
            AppLog.Error("DebugPage diagnostics failed: " + exc);
            StatusText.Text = exc.Message;
        }
    }

    private void BtnOpenFolder_Click(object sender, RoutedEventArgs e)
    {
        var dir = Path.GetDirectoryName(AppLog.LogFile) ?? AppSettings.DataDirectory;
        Directory.CreateDirectory(dir);
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
            AppLog.Error("DebugPage open folder failed: " + exc);
            StatusText.Text = exc.Message;
        }
    }
}
