using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.Analysis;
using RoNCT.App.Services;
using RoNCT.Core.Analysis;
using RoNCT.Core.Plan;
using RoNCT.Core.Scan;
using RoNCT.Core.Selection;

namespace RoNCT.App.Pages;

public sealed partial class TestPage : Page, ILocalizablePage
{
    private static readonly string[] KnownModFolders =
    {
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks",
        @"C:\Program Files\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks",
        @"D:\SteamLibrary\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks",
        @"E:\SteamLibrary\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks",
        @"F:\SteamLibrary\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks",
    };

    private MainWindow? _window;
    private IReadOnlyList<ModItem>? _analysisItems;
    private DeployPlan? _analysisPlan;
    private CancellationTokenSource? _runCts;
    private bool _runActive;

    public TestPage()
    {
        InitializeComponent();
        ApplyLanguage();
        ReloadSelection();
    }

    public ObservableCollection<ModRow> ModRows { get; } = new();
    public ObservableCollection<EdgeRow> EdgeRows { get; } = new();
    public ObservableCollection<UnresolvedRow> UnresolvedRows { get; } = new();
    public ObservableCollection<ErrorRow> ErrorRows { get; } = new();
    public ObservableCollection<GroupRow> GroupRows { get; } = new();

    public void AttachWindow(MainWindow window) =>
        _window = window;

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Test");
        PageBodyText.Text = Localizer.T("Page.Test.Body");
        SourceSectionText.Text = Localizer.T("Source.Title");
        BtnPickFolder.Content = Localizer.T("Source.PickFolder");
        BtnPickFiles.Content = Localizer.T("Source.PickFiles");
        BtnAutoDetect.Content = Localizer.T("Source.AutoDetect");
        BtnClear.Content = Localizer.T("Source.Clear");
        ActionSectionText.Text = Localizer.T("Action.Title");
        BtnTest.Content = Localizer.T("Action.Run");
        BtnAnalyze.Content = Localizer.T("Action.Analyze");
        BtnCancel.Content = Localizer.T("Action.Stop");
        AnalysisSectionText.Text = Localizer.T("Analysis.Section");
        BtnRunGroups.Content = Localizer.T("Analysis.RunGroups");
        BtnHideAnalysis.Content = Localizer.T("Analysis.Hide");
        EdgesPivotItem.Header = Localizer.T("Analysis.Edges");
        UnresolvedPivotItem.Header = Localizer.T("Analysis.Unresolved");
        ErrorsPivotItem.Header = Localizer.T("Analysis.Errors");
        GroupsPivotItem.Header = Localizer.T("Analysis.Groups");
        EdgeColFromHeader.Text = Localizer.T("Analysis.ColFrom");
        EdgeColToHeader.Text = Localizer.T("Analysis.ColTo");
        EdgeColAssetHeader.Text = Localizer.T("Analysis.ColAsset");
        EdgeColConfidenceHeader.Text = Localizer.T("Analysis.ColConfidence");
        UnresolvedColModHeader.Text = Localizer.T("Analysis.ColMod");
        UnresolvedColAssetHeader.Text = Localizer.T("Analysis.ColAsset");
        UnresolvedColRefHeader.Text = Localizer.T("Analysis.ColRef");
        ErrorColModHeader.Text = Localizer.T("Analysis.ColMod");
        ErrorColAssetHeader.Text = Localizer.T("Analysis.ColAsset");
        ErrorColErrorHeader.Text = Localizer.T("Analysis.ColError");
        GroupColIdHeader.Text = Localizer.T("Analysis.ColGroup");
        GroupColReasonHeader.Text = Localizer.T("Analysis.ColReason");
        GroupColFilesHeader.Text = Localizer.T("Analysis.ColFiles");
        GroupColEvidenceHeader.Text = Localizer.T("Analysis.ColEvidence");
        RefreshGroupRows();
        UpdateSelectionStatus();
    }

    private async void BtnPickFolder_Click(object sender, RoutedEventArgs e)
    {
        if (_window is null)
        {
            return;
        }

        var folder = await WindowsPicker.PickFolderAsync(
            _window, ResolvePickerStartDirectory());
        if (string.IsNullOrEmpty(folder))
        {
            return;
        }

        AppSettings.Current.ModFolder = folder;
        AppSettings.Current.SelectedPakFiles.Clear();
        AppSettings.Save();
        AppLog.UserAction("pick_mod_folder: " + folder);
        ReloadSelection();
    }

    private async void BtnPickFiles_Click(object sender, RoutedEventArgs e)
    {
        if (_window is null)
        {
            return;
        }

        var files = await WindowsPicker.PickPakFilesAsync(
            _window, ResolvePickerStartDirectory());
        if (files.Count == 0)
        {
            return;
        }

        AppSettings.Current.ModFolder = string.Empty;
        AppSettings.Current.SelectedPakFiles = files.ToList();
        AppSettings.Save();
        AppLog.UserAction($"pick_mod_files: {files.Count}");
        ReloadSelection();
    }

    private void BtnAutoDetect_Click(object sender, RoutedEventArgs e)
    {
        var gameRoot = AppSettings.Current.GameRoot;
        var paksRoot = !string.IsNullOrEmpty(gameRoot)
            ? Path.Combine(gameRoot, "ReadyOrNot", "Content", "Paks")
            : KnownModFolders.FirstOrDefault(Directory.Exists);

        if (string.IsNullOrEmpty(paksRoot) || !Directory.Exists(paksRoot))
        {
            LogText.Text = Localizer.T("Source.DetectFailed");
            return;
        }

        var mods = PakSource.FromGamePaksFolder(paksRoot);
        if (mods.Count == 0)
        {
            LogText.Text = Localizer.T("Source.DetectFailed");
            return;
        }

        AppSettings.Current.ModFolder = string.Empty;
        AppSettings.Current.SelectedPakFiles = mods.Select(mod => mod.FilePath).ToList();
        AppSettings.Save();
        AppLog.UserAction($"auto_detect_mods: {mods.Count}");
        ReloadSelection();
        LogText.Text = string.Format(Localizer.T("Source.DetectCount"), mods.Count);
    }

    private void RemoveRow_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string path })
        {
            var currentPaths = SelectionItems().Select(item => item.FilePath).ToList();
            currentPaths.Remove(path);
            AppSettings.Current.ModFolder = string.Empty;
            AppSettings.Current.SelectedPakFiles = currentPaths;
            AppSettings.Save();
            ReloadSelection();
        }
    }

    private void BtnClear_Click(object sender, RoutedEventArgs e)
    {
        AppSettings.Current.ModFolder = string.Empty;
        AppSettings.Current.SelectedPakFiles.Clear();
        AppSettings.Save();
        AppLog.UserAction("clear_mod_selection");
        ReloadSelection();
        LogText.Text = string.Empty;
    }

    private async void BtnTest_Click(object sender, RoutedEventArgs e)
    {
        if (_runActive)
        {
            return;
        }
        var items = SelectionItems();
        if (items.Count == 0)
        {
            LogText.Text = Localizer.T("Analysis.None");
            return;
        }

        await RunTestAsync(items, prebuiltPlan: null);
    }

    private async Task RunTestAsync(
        IReadOnlyList<ModItem> items,
        DeployPlan? prebuiltPlan)
    {
        if (_runActive)
        {
            return;
        }

        AppLog.UserAction(prebuiltPlan is null
            ? "v2_test_qt"
            : "v2_test_qt_from_analysis");
        _runActive = true;
        using var cts = new CancellationTokenSource();
        _runCts = cts;
        var queue = _window?.DispatcherQueue;
        SetRunningUi(true);
        try
        {
            var token = cts.Token;
            var result = await Task.Run(async () =>
                await TestRunner.RunAsync(
                    AppSettings.Current,
                    items,
                    line => queue?.TryEnqueue(() => LogText.Text = line),
                    token,
                    prebuiltPlan));

            if (token.IsCancellationRequested)
            {
                LogText.Text = Localizer.T("Action.Cancelled");
                return;
            }

            var total = result.Outcomes.Sum(outcome => outcome.Mods.Count);
            var ok = result.Outcomes
                .Where(o => o.Result.Verdict == TestVerdict.Ok)
                .Sum(o => o.Mods.Count);
            var fail = result.Outcomes
                .Where(o => o.Result.Verdict is TestVerdict.Fail or TestVerdict.Error)
                .Sum(o => o.Mods.Count);
            var skipped = result.Outcomes
                .Where(o => o.Result.Verdict == TestVerdict.Skipped)
                .Sum(o => o.Mods.Count);
            LogText.Text = string.Format(Localizer.T("Test.DoneSummary"),
                total, ok, fail, skipped)
                + "\n"
                + (result.CsvReport ?? string.Empty);
        }
        catch (OperationCanceledException)
        {
            LogText.Text = Localizer.T("Action.Cancelled");
        }
        catch (Exception exc)
        {
            LogText.Text = exc.Message;
        }
        finally
        {
            _runCts = null;
            _runActive = false;
            SetRunningUi(false);
        }
    }

    private async void BtnAnalyze_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("dependency_analysis_only");
        var items = SelectionItems();
        if (items.Count == 0)
        {
            LogText.Text = Localizer.T("Analysis.None");
            return;
        }

        Progress.Visibility = Visibility.Visible;
        try
        {
            var (graph, plan) = await Task.Run(async () =>
            {
                using var session = new Cue4AnalysisSession();
                var scan = await DependencyScanner.ScanGraphAsync(
                    repakExe: null,
                    dotnetExe: null,
                    uassetCliDll: null,
                    string.IsNullOrEmpty(AppSettings.Current.Engine)
                        ? "VER_UE5_4"
                        : AppSettings.Current.Engine,
                    items,
                    AppSettings.Current.AssetLimit > 0 ? AppSettings.Current.AssetLimit : 100,
                    default,
                    session,
                    session,
                    new Cue4AssetParser());
                var names = items
                    .Select(item => item.FileName)
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .ToArray();
                var deployPlan = DeploymentPlanner.Build(
                    names, scan.ConflictPairs, scan.Edges);
                return (scan, deployPlan);
            });

            _analysisItems = items;
            _analysisPlan = plan;
            PopulateAnalysis(graph);
            LogText.Text = string.Format(
                Localizer.T("Analysis.RunSummary"),
                graph.Paks,
                graph.ParsedAssets,
                graph.Edges.Count,
                graph.Unresolved,
                graph.ConflictCount);
        }
        catch (Exception exc)
        {
            LogText.Text = exc.Message;
        }
        finally
        {
            Progress.Visibility = Visibility.Collapsed;
        }
    }

    private void PopulateAnalysis(DependencyScanGraph graph)
    {
        EdgeRows.Clear();
        foreach (var edge in graph.EdgeDetails)
        {
            EdgeRows.Add(new EdgeRow(edge.FromMod, edge.ToMod, edge.AssetPath, edge.Confidence));
        }

        UnresolvedRows.Clear();
        foreach (var item in graph.UnresolvedReferences)
        {
            UnresolvedRows.Add(new UnresolvedRow(item.Mod, item.Asset, item.Reference));
        }

        ErrorRows.Clear();
        foreach (var item in graph.ParseErrors)
        {
            ErrorRows.Add(new ErrorRow(item.Mod, item.Asset, item.Error));
        }

        RefreshGroupRows();

        AnalysisSummaryText.Text = string.Format(
            Localizer.T("Analysis.DetailSummary"),
            graph.Paks,
            graph.ParsedAssets,
            graph.EdgeDetails.Count,
            graph.UnresolvedReferences.Count,
            graph.ParseErrors.Count,
            graph.ConflictCount,
            GroupRows.Count);
        AnalysisPanel.Visibility = Visibility.Visible;
    }

    private void RefreshGroupRows()
    {
        GroupRows.Clear();
        if (_analysisPlan is null)
        {
            return;
        }

        foreach (var group in _analysisPlan.Groups)
        {
            GroupRows.Add(new GroupRow(
                group.GroupId,
                LocalizeGroupReason(group.Reason),
                string.Join(", ", group.Mods),
                string.Join("；", group.Evidence)));
        }
    }

    private static string LocalizeGroupReason(string reason) =>
        Localizer.T(reason switch
        {
            "isolated" => "Analysis.Reason.Isolated",
            "dependency" => "Analysis.Reason.Dependency",
            "strong_dependency" => "Analysis.Reason.StrongDependency",
            "user_group" => "Analysis.Reason.UserGroup",
            _ => "Analysis.Reason.Unknown",
        });

    private async void BtnRunGroups_Click(object sender, RoutedEventArgs e)
    {
        if (_runActive)
        {
            return;
        }
        if (_analysisItems is null || _analysisItems.Count == 0 || _analysisPlan is null)
        {
            return;
        }

        await RunTestAsync(_analysisItems, _analysisPlan);
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        if (_runCts is null)
        {
            return;
        }

        AppLog.UserAction("cancel_test");
        _runCts.Cancel();
        BtnCancel.IsEnabled = false;
        LogText.Text = Localizer.T("Action.Cancelling");
    }

    private void SetRunningUi(bool running)
    {
        BtnTest.IsEnabled = !running;
        BtnAnalyze.IsEnabled = !running;
        BtnRunGroups.IsEnabled = !running && _analysisPlan is not null;
        BtnCancel.Visibility = running
            ? Visibility.Visible
            : Visibility.Collapsed;
        BtnCancel.IsEnabled = true;
        Progress.Visibility = running
            ? Visibility.Visible
            : Visibility.Collapsed;
    }

    private void BtnHideAnalysis_Click(object sender, RoutedEventArgs e)
    {
        AnalysisPanel.Visibility = Visibility.Collapsed;
    }

    private void ReloadSelection()
    {
        ModRows.Clear();
        var items = SelectionItems();
        foreach (var item in items)
        {
            ModRows.Add(new ModRow(item.FilePath, item.FileName, FormatSize(item.SizeBytes)));
        }
        UpdateSelectionStatus();
    }

    private IReadOnlyList<ModItem> SelectionItems()
    {
        var folder = AppSettings.Current.ModFolder;
        return !string.IsNullOrEmpty(folder)
            ? PakSource.FromFolder(folder)
            : PakSource.FromFiles(AppSettings.Current.SelectedPakFiles);
    }

    private void UpdateSelectionStatus()
    {
        SelectionStatusText.Text = ModRows.Count == 0
            ? Localizer.T("Source.None")
            : string.Format(Localizer.T("Source.Count"), ModRows.Count);
    }

    /// <summary>
    /// Opens the picker where the user is already working: the configured mod
    /// folder first, then the folder of an already selected .pak, then the
    /// detected Ready or Not mods directory. Falls back to the shell default
    /// only when none of those locations exist.
    /// </summary>
    private string? ResolvePickerStartDirectory() =>
        WindowsPicker.ResolveStartDirectory(
            AppSettings.Current.ModFolder,
            AppSettings.Current.SelectedPakFiles,
            AppSettings.Current.GameRoot,
            KnownModFolders);

    private static string FormatSize(long bytes)
    {
        const double mb = 1024 * 1024;
        return bytes >= mb
            ? $"{bytes / mb:0.0} MB"
            : $"{bytes / 1024:0} KB";
    }
}

public sealed class ModRow
{
    public ModRow(string filePath, string fileName, string fileSize)
    {
        FilePath = filePath;
        FileName = fileName;
        FileSize = fileSize;
    }

    public string FilePath { get; }
    public string FileName { get; }
    public string FileSize { get; }
}

public sealed class EdgeRow
{
    public EdgeRow(string source, string target, string asset, string confidence)
    {
        Source = source;
        Target = target;
        Asset = asset;
        Confidence = confidence;
    }

    public string Source { get; }
    public string Target { get; }
    public string Asset { get; }
    public string Confidence { get; }
}

public sealed class UnresolvedRow
{
    public UnresolvedRow(string mod, string asset, string reference)
    {
        Mod = mod;
        Asset = asset;
        Reference = reference;
    }

    public string Mod { get; }
    public string Asset { get; }
    public string Reference { get; }
}

public sealed class ErrorRow
{
    public ErrorRow(string mod, string asset, string error)
    {
        Mod = mod;
        Asset = asset;
        Error = error;
    }

    public string Mod { get; }
    public string Asset { get; }
    public string Error { get; }
}

public sealed class GroupRow
{
    public GroupRow(string groupId, string reason, string mods, string evidence)
    {
        GroupId = groupId;
        Reason = reason;
        Mods = mods;
        Evidence = evidence;
    }

    public string GroupId { get; }
    public string Reason { get; }
    public string Mods { get; }
    public string Evidence { get; }
}
