using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using RoNCT.App.Pages;
using RoNCT.App.Services;

namespace RoNCT.App;

public sealed partial class MainWindow : Window
{
    private readonly Dictionary<string, Page> _pages = new();
    private bool _initializingTheme;

    public MainWindow()
    {
        InitializeComponent();

        ExtendsContentIntoTitleBar = true;
        SetTitleBar(AppTitleBar);
        AppWindow.TitleBar.PreferredHeightOption = TitleBarHeightOption.Tall;

        var iconPath = Path.Combine(AppContext.BaseDirectory, "Assets", "AppIcon.ico");
        if (File.Exists(iconPath))
        {
            AppWindow.SetIcon(iconPath);
        }

        try
        {
            SystemBackdrop = new MicaBackdrop();
        }
        catch
        {
            // Mica requires Windows 11; older systems keep the solid fallback.
        }

        ApplyLanguage();
        RebuildThemeCombo(AppSettings.Current.ThemeMode);
        ShowPage("test");
        VersionText.Text = $"v{GetInformationalVersion()}";
    }

    private static string GetInformationalVersion()
    {
        var assembly = typeof(MainWindow).Assembly;
        var attribute = assembly
            .GetCustomAttributes(typeof(System.Reflection.AssemblyInformationalVersionAttribute), false)
            .OfType<System.Reflection.AssemblyInformationalVersionAttribute>()
            .FirstOrDefault();
        var raw = attribute?.InformationalVersion ?? assembly.GetName().Version?.ToString() ?? "0.0.0";
        return raw.Split('+')[0];
    }

    private void TitleBar_PaneToggleRequested(TitleBar sender, object args)
    {
        NavView.IsPaneOpen = !NavView.IsPaneOpen;
    }

    private void NavView_SelectionChanged(
        NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItem is NavigationViewItem { Tag: string tag })
        {
            ShowPage(tag);
        }
    }

    private void ShowPage(string tag)
    {
        var type = tag switch
        {
            "test" => typeof(TestPage),
            "nexus" => typeof(NexusPage),
            "backup" => typeof(BackupPage),
            "quarantine" => typeof(QuarantinePage),
            "advanced" => typeof(AdvancedPage),
            _ => typeof(TestPage),
        };

        if (!_pages.TryGetValue(tag, out var page))
        {
            page = (Page)Activator.CreateInstance(type)!;
            _pages[tag] = page;
        }

        NavFrame.Content = page;
    }

    private void ThemeCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_initializingTheme)
        {
            return;
        }

        var mode = ThemeCombo.SelectedIndex switch
        {
            0 => "system",
            1 => "light",
            _ => "dark",
        };
        AppSettings.Current.ThemeMode = mode;
        AppSettings.Save();
        SelectTheme(mode);
    }

    private void SelectTheme(string mode)
    {
        NavView.RequestedTheme = mode switch
        {
            "light" => ElementTheme.Light,
            "dark" => ElementTheme.Dark,
            _ => ElementTheme.Default,
        };
    }

    private void LangEnButton_Click(object sender, RoutedEventArgs e)
    {
        SetLanguage(Localizer.English);
        ApplyLanguage();
    }

    private void LangZhButton_Click(object sender, RoutedEventArgs e)
    {
        SetLanguage(Localizer.Chinese);
        ApplyLanguage();
    }

    private static void SetLanguage(string language)
    {
        Localizer.SetLanguage(language);
        AppSettings.Current.Language = language;
        AppSettings.Save();
    }

    private void ApplyLanguage()
    {
        NavTestItem.Content = Localizer.T("Nav.Test");
        NavNexusItem.Content = Localizer.T("Nav.Nexus");
        NavBackupItem.Content = Localizer.T("Nav.Backup");
        NavQuarantineItem.Content = Localizer.T("Nav.Quarantine");
        NavAdvancedItem.Content = Localizer.T("Nav.Advanced");
        ThemeLabel.Text = Localizer.T("Footer.Theme");
        LanguageLabel.Text = Localizer.T("Footer.Language");
        RebuildThemeCombo(null);

        foreach (var page in _pages.Values)
        {
            if (page is ILocalizablePage localizable)
            {
                localizable.ApplyLanguage();
            }
        }
    }

    private void RebuildThemeCombo(string? mode)
    {
        _initializingTheme = true;
        try
        {
            var selected = ThemeCombo.SelectedIndex;
            ThemeCombo.Items.Clear();
            ThemeCombo.Items.Add(Localizer.T("Theme.System"));
            ThemeCombo.Items.Add(Localizer.T("Theme.Light"));
            ThemeCombo.Items.Add(Localizer.T("Theme.Dark"));
            ThemeCombo.SelectedIndex = mode switch
            {
                "light" => 1,
                "dark" => 2,
                _ when mode is null && selected >= 0 => selected,
                _ => 0,
            };
        }
        finally
        {
            _initializingTheme = false;
        }
    }
}
