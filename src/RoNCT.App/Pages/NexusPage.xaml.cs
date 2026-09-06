using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;
using RoNCT.Core.Selection;

namespace RoNCT.App.Pages;

public sealed partial class NexusPage : Page, ILocalizablePage
{
    private readonly List<NexusModInfo> _identified = new();

    public NexusPage()
    {
        InitializeComponent();
        ApplyLanguage();
        ApiKeyBox.Password = AppSettings.Current.NexusApiKey;
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Nexus");
        PageBodyText.Text = Localizer.T("Page.Nexus.Body");
        KeyLabel.Text = Localizer.T("Nexus.ApiKey");
        BtnSaveKey.Content = Localizer.T("Nexus.SaveKey");
        BtnIdentify.Content = Localizer.T("Nexus.Identify");
        BtnDeps.Content = Localizer.T("Nexus.Deps");
    }

    private void BtnSaveKey_Click(object sender, RoutedEventArgs e)
    {
        AppSettings.Current.NexusApiKey = ApiKeyBox.Password;
        AppSettings.Save();
        StatusText.Text = Localizer.T("Nexus.Saved");
    }

    private async void BtnIdentify_Click(object sender, RoutedEventArgs e)
    {
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

        ResultList.Items.Clear();
        _identified.Clear();
        StatusText.Text = Localizer.T("Nexus.Identifying");
        foreach (var mod in mods)
        {
            var md5 = NexusClient.Md5(mod.FilePath);
            var info = await NexusClient.GetModByMd5Async(key, md5);
            var line = info is not null
                ? $"{mod.FileName}  ->  {info.Name} ({info.ModId})"
                : $"{mod.FileName}  ->  {Localizer.T("Nexus.NotFound")}";
            ResultList.Items.Add(line);
            if (info is not null)
            {
                _identified.Add(info);
            }
        }
        StatusText.Text = string.Format(
            Localizer.T("Nexus.Identified"), _identified.Count, mods.Count);
    }

    private async void BtnDeps_Click(object sender, RoutedEventArgs e)
    {
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

        ResultList.Items.Clear();
        foreach (var line in missing.Distinct())
        {
            ResultList.Items.Add(line);
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
