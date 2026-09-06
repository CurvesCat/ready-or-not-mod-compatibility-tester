using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;
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
        var autoFolder = AppSettings.Current.GameRoot;
        var folder = !string.IsNullOrEmpty(autoFolder)
            ? Path.Combine(autoFolder, "ReadyOrNot", "Content", "Paks")
            : KnownModFolders.FirstOrDefault(Directory.Exists);

        if (string.IsNullOrEmpty(folder) || !Directory.Exists(folder))
        {
            LogText.Text = Localizer.T("Source.DetectFailed");
            return;
        }

        AppSettings.Current.ModFolder = folder;
        AppSettings.Current.SelectedPakFiles.Clear();
        AppSettings.Save();
        ReloadSelection();
        LogText.Text = Localizer.T("Source.DetectOk");
    }

    private void RemoveRow_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string path })
        {
            AppSettings.Current.SelectedPakFiles.Remove(path);
            AppSettings.Save();
            ReloadSelection();
        }
    }

    private void BtnTest_Click(object sender, RoutedEventArgs e) =>
        LogText.Text = Localizer.T("Action.PipelineSoon");

    private void BtnAnalyze_Click(object sender, RoutedEventArgs e) =>
        LogText.Text = Localizer.T("Action.PipelineSoon");

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
