using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
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

    public TestPage()
    {
        InitializeComponent();
        ApplyLanguage();
        ReloadSelection();
    }

    public ObservableCollection<ModRow> ModRows { get; } = new();

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
        UpdateSelectionStatus();
    }

    private async void BtnPickFolder_Click(object sender, RoutedEventArgs e)
    {
        if (_window is null)
        {
            return;
        }

        var folder = await WindowsPicker.PickFolderAsync(_window);
        if (string.IsNullOrEmpty(folder))
        {
            return;
        }

        AppSettings.Current.ModFolder = folder;
        AppSettings.Current.SelectedPakFiles.Clear();
        AppSettings.Save();
        ReloadSelection();
    }

    private async void BtnPickFiles_Click(object sender, RoutedEventArgs e)
    {
        if (_window is null)
        {
            return;
        }

        var files = await WindowsPicker.PickPakFilesAsync(_window);
        if (files.Count == 0)
        {
            return;
        }

        AppSettings.Current.ModFolder = string.Empty;
        AppSettings.Current.SelectedPakFiles = files.ToList();
        AppSettings.Save();
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
        ReloadSelection();
        LogText.Text = string.Empty;
    }

    private async void BtnTest_Click(object sender, RoutedEventArgs e)
    {
        var items = SelectionItems();
        if (items.Count == 0)
        {
            LogText.Text = Localizer.T("Analysis.None");
            return;
        }

        Progress.Visibility = Visibility.Visible;
        try
        {
            var result = await TestRunner.RunAsync(
                AppSettings.Current, items, line => LogText.Text = line, default);
            Progress.Visibility = Visibility.Collapsed;

            var ok = result.Outcomes.Count(o => o.Result.Verdict == TestVerdict.Ok);
            var fail = result.Outcomes.Count(o => o.Result.Verdict is TestVerdict.Fail or TestVerdict.Error);
            var skipped = result.Outcomes.Count(o => o.Result.Verdict == TestVerdict.Skipped);
            LogText.Text = string.Format(Localizer.T("Test.DoneSummary"),
                result.Outcomes.Count, ok, fail, skipped)
                + "\n"
                + (result.CsvReport ?? string.Empty);
        }
        catch (Exception exc)
        {
            Progress.Visibility = Visibility.Collapsed;
            LogText.Text = exc.Message;
        }
    }

    private async void BtnAnalyze_Click(object sender, RoutedEventArgs e)
    {
        var items = SelectionItems();
        if (items.Count == 0)
        {
            LogText.Text = Localizer.T("Analysis.None");
            return;
        }

        var repak = ResolveRepakExe();
        var dotnet = ResolveDotnetExe();
        var cli = ResolveUAssetCliDll();
        if (string.IsNullOrEmpty(repak) || !File.Exists(repak) ||
            string.IsNullOrEmpty(dotnet) || !File.Exists(dotnet) ||
            string.IsNullOrEmpty(cli) || !File.Exists(cli))
        {
            LogText.Text = Localizer.T("Analysis.ToolMissing");
            return;
        }

        Progress.Visibility = Visibility.Visible;
        var result = await DependencyScanner.RunAsync(
            repak,
            dotnet,
            cli,
            string.IsNullOrEmpty(AppSettings.Current.Engine) ? "VER_UE5_4" : AppSettings.Current.Engine,
            items,
            AppSettings.Current.AssetLimit > 0 ? AppSettings.Current.AssetLimit : 100);
        Progress.Visibility = Visibility.Collapsed;

        LogText.Text = string.Format(
            Localizer.T("Analysis.RunSummary"),
            result.Paks,
            result.ParsedAssets,
            result.Edges,
            result.Unresolved,
            result.Conflicts);
    }

    private static string ResolveRepakExe()
    {
        var configured = AppSettings.Current.RepakExe;
        if (!string.IsNullOrEmpty(configured) && File.Exists(configured))
        {
            return configured;
        }

        var known = @"C:\Users\curve\Documents\Codex\2026-09-05\call-zhi\work\tools\repak\repak.exe";
        return File.Exists(known) ? known : configured ?? string.Empty;
    }

    private static string ResolveDotnetExe()
    {
        var configured = AppSettings.Current.DotnetExe;
        if (!string.IsNullOrEmpty(configured) && File.Exists(configured))
        {
            return configured;
        }

        var known = @"C:\Users\curve\Documents\Codex\2026-09-05\call-zhi\work\tools\dotnet10\dotnet.exe";
        return File.Exists(known) ? known : configured ?? string.Empty;
    }

    private static string ResolveUAssetCliDll()
    {
        var configured = AppSettings.Current.UAssetCliDll;
        if (!string.IsNullOrEmpty(configured) && File.Exists(configured))
        {
            return configured;
        }

        var known = @"C:\Users\curve\Documents\Codex\2026-09-05\call-zhi\work\tools\UAssetCLI\UAssetCLI\UAssetCLI.dll";
        return File.Exists(known) ? known : configured ?? string.Empty;
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
