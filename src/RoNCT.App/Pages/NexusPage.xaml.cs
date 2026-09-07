using System.Collections.ObjectModel;
using System.Diagnostics;
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
    private bool _dialogOpen;
    private Dictionary<string, NexusMappingRecord> _mapping = new(
        StringComparer.OrdinalIgnoreCase);

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
        BtnOpenResult.Content = Localizer.T("Nexus.OpenPage");
        BtnConfirmResult.Content = Localizer.T("Nexus.Confirm");
        BtnCandidatesResult.Content = Localizer.T("Nexus.Candidates");
        BtnIgnoreResult.Content = Localizer.T("Nexus.Ignore");
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
            Content = Localizer.T("Nexus.OpenApiPage"),
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
            Children = { steps, openButton, copyButton },
        };

        var dialog = new ContentDialog
        {
            Title = Localizer.T("Nexus.TutorialTitle"),
            Content = content,
            CloseButtonText = Localizer.T("Nexus.TutorialClose"),
            XamlRoot = XamlRoot,
        };
        dialog.Closed += (_, _) => _window?.SetAlwaysOnTop(false);
        await ShowExclusiveDialogAsync(dialog);
    }

    private void OpenApiPage_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("nexus_open_api_page");
        OpenUrl(ApiKeyUrl);
        StatusText.Text = Localizer.T("Nexus.PageOpened");
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
        _mapping = NexusUserMapping.Load();
        var found = 0;
        var candidates = 0;
        var confirmed = 0;
        var ignored = 0;
        var errors = 0;

        foreach (var mod in mods)
        {
            StatusText.Text = Localizer.T("Nexus.Identifying") + "  " + mod.FileName;
            try
            {
                var md5 = NexusClient.Md5(mod.FilePath);
                if (_mapping.TryGetValue(md5, out var saved) &&
                    !string.IsNullOrEmpty(saved.Choice))
                {
                    if (saved.Choice == NexusUserMapping.Confirmed)
                    {
                        confirmed++;
                        var info = ToInfo(saved);
                        AddIdentified(info);
                        ResultRows.Add(RowFromInfo(
                            mod.FileName,
                            md5,
                            Localizer.T("Nexus.Status.Confirmed"),
                            info,
                            candidates: null));
                    }
                    else
                    {
                        ignored++;
                        ResultRows.Add(new NexusResultRow(
                            mod.FileName,
                            md5,
                            modId: null,
                            Localizer.T("Nexus.Status.Ignored"),
                            string.Empty,
                            string.Empty,
                            string.Empty));
                    }
                    continue;
                }

                var matches = await NexusClient.SearchMd5Async(key, md5);
                if (matches.Count > 0)
                {
                    found++;
                    var info = matches[0];
                    AddIdentified(info);
                    ResultRows.Add(RowFromInfo(
                        mod.FileName,
                        md5,
                        Localizer.T("Nexus.Status.Found"),
                        info,
                        matches));
                    continue;
                }

                var candidateList = await NexusClient.SearchCandidatesAsync(
                    key, mod.FileName);
                var best = candidateList.FirstOrDefault();
                if (best is not null)
                {
                    candidates++;
                    AddIdentified(best);
                    ResultRows.Add(RowFromInfo(
                        mod.FileName,
                        md5,
                        Localizer.T("Nexus.Status.Candidate"),
                        best,
                        candidateList));
                }
                else
                {
                    ResultRows.Add(new NexusResultRow(
                        mod.FileName,
                        md5,
                        modId: null,
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
                    string.Empty,
                    modId: null,
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
            confirmed,
            ignored,
            errors,
            mods.Count);
        if (ResultRows.Count > 0)
        {
            ResultList.SelectedIndex = 0;
        }
    }

    private NexusResultRow RowFromInfo(
        string fileName,
        string md5,
        string status,
        NexusModInfo info,
        IReadOnlyList<NexusModInfo>? candidates)
    {
        return new NexusResultRow(
            fileName,
            md5,
            info.ModId,
            status,
            info.Name ?? Localizer.T("Nexus.NotFound"),
            info.Author ?? info.FileName ?? string.Empty,
            info.ModUrl ?? string.Empty,
            candidates);
    }

    private void AddIdentified(NexusModInfo? info)
    {
        if (info is not null && info.ModId is not null)
        {
            _identified.RemoveAll(item => item.ModId == info.ModId);
            _identified.Add(info);
        }
    }

    private static NexusModInfo ToInfo(NexusMappingRecord record)
    {
        return new NexusModInfo
        {
            ModId = record.ModId,
            Name = record.ModName,
            Author = record.Author,
            ModUrl = record.ModUrl,
        };
    }

    private NexusResultRow? CurrentRow =>
        ResultList.SelectedItem as NexusResultRow;

    private void ResultList_SelectionChanged(
        object sender, SelectionChangedEventArgs e)
    {
        var hasRow = CurrentRow is not null;
        BtnOpenResult.IsEnabled = hasRow;
        BtnConfirmResult.IsEnabled = hasRow;
        BtnCandidatesResult.IsEnabled = hasRow;
        BtnIgnoreResult.IsEnabled = hasRow;
    }

    private void BtnOpenResult_Click(object sender, RoutedEventArgs e)
    {
        var row = CurrentRow;
        if (row is null)
        {
            return;
        }
        if (string.IsNullOrEmpty(row.Url))
        {
            StatusText.Text = Localizer.T("Nexus.NoCandidate");
            return;
        }
        OpenUrl(row.Url);
    }

    private async void BtnConfirmResult_Click(object sender, RoutedEventArgs e)
    {
        var row = CurrentRow;
        if (row is null)
        {
            return;
        }

        if (row.ModId is not null && !string.IsNullOrEmpty(row.Url))
        {
            ConfirmRow(row, new NexusModInfo
            {
                ModId = row.ModId,
                Name = row.Detail,
                Author = row.Author,
                ModUrl = row.Url,
            });
            return;
        }

        if (row.Candidates.Count > 0)
        {
            await ChooseCandidateAsync(row);
            return;
        }

        StatusText.Text = Localizer.T("Nexus.NoCandidate");
    }

    private async void BtnCandidatesResult_Click(object sender, RoutedEventArgs e)
    {
        var row = CurrentRow;
        if (row is not null)
        {
            await ChooseCandidateAsync(row);
        }
    }

    private async Task ChooseCandidateAsync(NexusResultRow row)
    {
        if (row.Candidates.Count == 0)
        {
            StatusText.Text = Localizer.T("Nexus.NoCandidate");
            return;
        }

        var labels = row.Candidates
            .Select(candidate =>
            {
                var name = candidate.Name ?? string.Empty;
                var author = candidate.Author ?? string.Empty;
                return string.IsNullOrEmpty(author) ? name : $"{name} — {author}";
            })
            .ToList();
        var list = new ListView
        {
            MaxHeight = 320,
            SelectionMode = ListViewSelectionMode.Single,
            ItemsSource = labels,
        };
        if (labels.Count > 0)
        {
            list.SelectedIndex = 0;
        }

        var content = new StackPanel
        {
            MinWidth = 380,
            Children =
            {
                new TextBlock
                {
                    Text = Localizer.T("Nexus.CandidatesHint"),
                    TextWrapping = TextWrapping.Wrap,
                    Margin = new Thickness(0, 0, 0, 10),
                    Opacity = 0.8,
                },
                list,
            },
        };

        var dialog = new ContentDialog
        {
            Title = string.Format(
                Localizer.T("Nexus.CandidatesTitle"), row.FileName),
            Content = content,
            PrimaryButtonText = Localizer.T("Nexus.ConfirmCandidate"),
            CloseButtonText = Localizer.T("Nexus.TutorialClose"),
            XamlRoot = XamlRoot,
        };

        var result = await ShowExclusiveDialogAsync(dialog);
        if (result != ContentDialogResult.Primary || list.SelectedIndex < 0)
        {
            return;
        }

        var candidate = row.Candidates[list.SelectedIndex];
        ConfirmRow(row, candidate);
    }

    private void ConfirmRow(NexusResultRow row, NexusModInfo info)
    {
        if (string.IsNullOrEmpty(row.Md5))
        {
            StatusText.Text = Localizer.T("Nexus.NeedMd5");
            return;
        }

        NexusUserMapping.Confirm(
            row.Md5,
            info.ModId,
            info.Name ?? string.Empty,
            info.ModUrl ?? string.Empty,
            row.FileName,
            info.Author ?? string.Empty);
        _mapping = NexusUserMapping.Load();
        AddIdentified(info);

        row.Status = Localizer.T("Nexus.Status.Confirmed");
        row.Detail = info.Name ?? row.Detail;
        row.Author = info.Author ?? string.Empty;
        row.Url = info.ModUrl ?? string.Empty;
        StatusText.Text = string.Format(
            Localizer.T("Nexus.ConfirmSaved"), info.Name ?? row.FileName);
    }

    /// <summary>
    /// WinUI allows only one ContentDialog per XamlRoot at a time. This guard
    /// prevents a second click/event from trying to open another dialog while
    /// one is still visible, which would crash with a COM exception.
    /// </summary>
    private async Task<ContentDialogResult> ShowExclusiveDialogAsync(
        ContentDialog dialog)
    {
        if (_dialogOpen)
        {
            return ContentDialogResult.None;
        }

        _dialogOpen = true;
        try
        {
            return await dialog.ShowAsync();
        }
        finally
        {
            _dialogOpen = false;
        }
    }

    private void BtnIgnoreResult_Click(object sender, RoutedEventArgs e)
    {
        var row = CurrentRow;
        if (row is null)
        {
            return;
        }
        if (string.IsNullOrEmpty(row.Md5))
        {
            StatusText.Text = Localizer.T("Nexus.NeedMd5");
            return;
        }

        NexusUserMapping.Ignore(row.Md5, row.FileName);
        _mapping = NexusUserMapping.Load();
        _identified.RemoveAll(info => info.ModId is not null &&
                                     info.ModId == row.ModId);
        row.Status = Localizer.T("Nexus.Status.Ignored");
        row.Detail = string.Empty;
        row.Author = string.Empty;
        row.Url = string.Empty;
        StatusText.Text = Localizer.T("Nexus.IgnoredSaved");
    }

    private async void BtnDeps_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("nexus_deps_start");
        var key = ApiKeyBox.Password;
        if (string.IsNullOrEmpty(key))
        {
            StatusText.Text = Localizer.T("Nexus.NoKey");
            return;
        }

        _mapping = NexusUserMapping.Load();
        foreach (var record in _mapping.Values)
        {
            if (record.Choice == NexusUserMapping.Confirmed)
            {
                AddIdentified(ToInfo(record));
            }
        }

        var mods = _identified
            .Where(info => info.ModId is not null)
            .DistinctBy(info => info.ModId)
            .ToList();
        if (mods.Count == 0)
        {
            StatusText.Text = Localizer.T("Nexus.IdentifyFirst");
            return;
        }

        StatusText.Text = Localizer.T("Nexus.CheckingDeps");
        var missing = new List<string>();
        foreach (var info in mods)
        {
            if (info.ModId is null)
            {
                continue;
            }
            foreach (var dep in await NexusClient.GetDependenciesAsync(
                         key, info.ModId.Value))
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
                string.Empty,
                modId: null,
                Localizer.T("Nexus.Dep"),
                parts.Length > 1 ? parts[1] : line,
                string.Empty,
                string.Empty));
        }
        StatusText.Text = string.Format(Localizer.T("Nexus.DepsSummary"), missing.Count);
    }

    private static void OpenUrl(string url)
    {
        try
        {
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch (Exception exc)
        {
            AppLog.Error("NexusPage open URL failed: " + exc.Message);
        }
    }

    private static IReadOnlyList<ModItem> CurrentSelection()
    {
        var folder = AppSettings.Current.ModFolder;
        return !string.IsNullOrEmpty(folder)
            ? PakSource.FromFolder(folder)
            : PakSource.FromFiles(AppSettings.Current.SelectedPakFiles);
    }
}
