using System.Diagnostics;
using System.Collections.ObjectModel;
using Windows.ApplicationModel.DataTransfer;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;
using RoNCT.Core.Selection;

namespace RoNCT.App.Pages;

public sealed partial class NexusPage : Page, ILocalizablePage
{
    private const string ApiKeyUrl = "https://www.nexusmods.com/settings/api-keys";

    private readonly List<NexusModInfo> _identified = new();
    private MainWindow? _window;

    public ObservableCollection<NexusResultRow> ResultRows { get; } = new();

    public NexusPage()
    {
        InitializeComponent();
        ApplyLanguage();
        ApiKeyBox.Password = AppSettings.Current.NexusApiKey;
    }

    public void AttachWindow(MainWindow window) =>
        _window = window;

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Nexus");
        PageBodyText.Text = Localizer.T("Page.Nexus.Body");
        KeyLabel.Text = Localizer.T("Nexus.ApiKey");
        BtnSaveKey.Content = Localizer.T("Nexus.SaveKey");
        BtnTutorial.Content = Localizer.T("Nexus.Tutorial");
        BtnIdentify.Content = Localizer.T("Nexus.Identify");
        BtnDeps.Content = Localizer.T("Nexus.Deps");
    }

    private async void BtnTutorial_Click(object sender, RoutedEventArgs e)
    {
        _window?.SetAlwaysOnTop(true);

        var steps = new TextBlock
        {
            Text = Localizer.T("Nexus.TutorialSteps"),
            TextWrapping = TextWrapping.Wrap,
            Margin = new Thickness(0, 0, 0, 12),
        };

        var openButton = new Button
        {
            Content = Localizer.T("Nexus.OpenPage"),
            HorizontalAlignment = HorizontalAlignment.Stretch,
            Margin = new Thickness(0, 0, 0, 8),
        };
        openButton.Click += OpenApiPage_Click;

        var copyButton = new Button
        {
            Content = Localizer.T("Nexus.CopyLink"),
            HorizontalAlignment = HorizontalAlignment.Stretch,
            Margin = new Thickness(0, 0, 0, 8),
        };
        copyButton.Click += CopyApiLink_Click;

        var content = new StackPanel
        {
            MinWidth = 320,
            Children =
            {
                steps,
                openButton,
                copyButton,
            },
        };

        var dialog = new ContentDialog
        {
            Title = Localizer.T("Nexus.TutorialTitle"),
            Content = content,
            CloseButtonText = Localizer.T("Nexus.TutorialClose"),
            XamlRoot = XamlRoot,
        };
        dialog.Closed += (_, _) => _window?.SetAlwaysOnTop(false);
        await dialog.ShowAsync();
    }

    private void OpenApiPage_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("nexus_open_api_page");
        try
        {
            Process.Start(new ProcessStartInfo(ApiKeyUrl)
            {
                UseShellExecute = true,
            });
            StatusText.Text = Localizer.T("Nexus.PageOpened");
        }
        catch (Exception exc)
        {
            AppLog.Error("NexusPage open API page failed: " + exc.Message);
            StatusText.Text = exc.Message;
        }
    }

    private void CopyApiLink_Click(object sender, RoutedEventArgs e)
    {
        var package = new DataPackage();
        package.SetText(ApiKeyUrl);
        Clipboard.SetContent(package);
        StatusText.Text = Localizer.T("Nexus.LinkCopied");
    }

    private void BtnSaveKey_Click(object sender, RoutedEventArgs e)
    {
        AppSettings.Current.NexusApiKey = ApiKeyBox.Password;
        AppSettings.Save();
        AppLog.UserAction("nexus_key_saved");
        StatusText.Text = Localizer.T("Nexus.Saved");
    }

    private async void BtnIdentify_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("nexus_identify_start");
        var key = ApiKeyBox.Password;
        if (string.IsNullOrEmpty(key))
        {
            StatusText.Text = Localizer.T("Nexus.NoKey");
            return;
        }

        var mods = CurrentSelection();
        if (mods.Count == 0)
        {
            StatusText.Text = Localizer.T("Analysis.None");
            return;
        }

        ResultRows.Clear();
        _identified.Clear();
        StatusText.Text = Localizer.T("Nexus.Identifying");
        var found = 0;
        var candidates = 0;
        var errors = 0;
        foreach (var mod in mods)
        {
            StatusText.Text = Localizer.T("Nexus.Identifying") + "  " + mod.FileName;
            try
            {
                var md5 = NexusClient.Md5(mod.FilePath);
                var matches = await NexusClient.SearchMd5Async(key, md5);
                if (matches.Count > 0)
                {
                    var info = matches[0];
                    _identified.Add(info);
                    found++;
                    ResultRows.Add(new NexusResultRow(
                        mod.FileName,
                        Localizer.T("Nexus.Status.Found"),
                        info.Name ?? mod.FileName,
                        info.Author ?? string.Empty,
                        info.ModUrl ?? string.Empty));
                    continue;
                }

                var best = await FindBestCandidateAsync(key, mod.FileName);
                if (best is not null)
                {
                    _identified.Add(best);
                    candidates++;
                    ResultRows.Add(new NexusResultRow(
                        mod.FileName,
                        Localizer.T("Nexus.Status.Candidate"),
                        best.Name ?? Localizer.T("Nexus.NotFound"),
                        best.Author ?? string.Empty,
                        best.ModUrl ?? string.Empty));
                }
                else
                {
                    ResultRows.Add(new NexusResultRow(
                        mod.FileName,
                        Localizer.T("Nexus.Status.Unknown"),
                        string.Empty,
                        string.Empty,
                        string.Empty));
                }
            }
            catch (Exception exc)
            {
                errors++;
                AppLog.Error($"NexusPage identify failed for {mod.FileName}: {exc.Message}");
                ResultRows.Add(new NexusResultRow(
                    mod.FileName,
                    Localizer.T("Nexus.Status.Error"),
                    exc.Message,
                    string.Empty,
                    string.Empty));
            }
        }

        StatusText.Text = string.Format(
            Localizer.T("Nexus.IdentifySummary"),
            found,
            candidates,
            errors,
            mods.Count);
    }

    private static async Task<NexusModInfo?> FindBestCandidateAsync(
        string key,
        string fileName)
    {
        var candidates = await NexusClient.SearchCandidatesAsync(key, fileName);
        return candidates.FirstOrDefault();
    }

    private async void ResultList_ItemClick(object sender, ItemClickEventArgs e)
    {
        if (e.ClickedItem is not NexusResultRow { Url: string url } || !Uri.IsWellFormedUriString(url, UriKind.Absolute))
        {
            return;
        }
        try
        {
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch (Exception exc)
        {
            AppLog.Error("NexusPage open result failed: " + exc.Message);
        }
    }

    private async void BtnDeps_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("nexus_deps_start");
        var key = ApiKeyBox.Password;
        if (string.IsNullOrEmpty(key) || _identified.Count == 0)
        {
            StatusText.Text = Localizer.T("Nexus.IdentifyFirst");
            return;
        }

        StatusText.Text = Localizer.T("Nexus.CheckingDeps");
        var missing = new List<string>();
        foreach (var info in _identified)
        {
            if (info.ModId is null)
            {
                continue;
            }
            foreach (var dep in await NexusClient.GetDependenciesAsync(key, info.ModId.Value))
            {
                if (!string.IsNullOrEmpty(dep.Name))
                {
                    missing.Add($"{info.Name} needs {dep.Name}");
                }
            }
        }

        ResultRows.Clear();
        foreach (var line in missing.Distinct())
        {
            var parts = line.Split(" needs ", 2);
            ResultRows.Add(new NexusResultRow(
                parts.Length > 0 ? parts[0] : line,
                Localizer.T("Nexus.Dep"),
                parts.Length > 1 ? parts[1] : line,
                string.Empty,
                string.Empty));
        }
        StatusText.Text = string.Format(Localizer.T("Nexus.DepsSummary"), missing.Count);
    }

    private static IReadOnlyList<ModItem> CurrentSelection()
    {
        var folder = AppSettings.Current.ModFolder;
        return !string.IsNullOrEmpty(folder)
            ? PakSource.FromFolder(folder)
            : PakSource.FromFiles(AppSettings.Current.SelectedPakFiles);
    }
}
