using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Media.Imaging;
using System.Runtime.InteropServices;
using System.Diagnostics;
using RoNCT.App.Pages;
using RoNCT.App.Services;

namespace RoNCT.App;

public sealed partial class MainWindow : Window
{
    private const string AppDisplayName = "RoN Mod 兼容性测试器";
    private const string Author = "CurvesCat";
    private const string ContactEmail = "ronct.dev@icloud.com";
    private const string GitHubUrl =
        "https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester";
    private const string LicenseName = "PolyForm Noncommercial 1.0.0";

    private readonly Dictionary<string, Page> _pages = new();
    private bool _initializingTheme;
    private bool _dialogOpen;
    private nint _windowIcon;

    public MainWindow()
    {
        InitializeComponent();
        Closed += (_, _) => AppLog.Log("GUI closed");

        FooterPanel.Visibility = NavView.IsPaneOpen ? Visibility.Visible : Visibility.Collapsed;

        ExtendsContentIntoTitleBar = true;
        SetTitleBar(AppTitleBar);
        AppWindow.Resize(new Windows.Graphics.SizeInt32(1120, 720));

        var iconPath = Path.Combine(AppContext.BaseDirectory, "Assets", "AppIcon.ico");
        if (File.Exists(iconPath))
        {
            AppWindow.SetIcon(iconPath);
            ApplyTaskbarIcon(iconPath);
        }

        // The translucent system backdrop follows the OS theme, which keeps the
        // title bar and navigation pane dark even in Light mode. Until the theme
        // is driven through a system-backdrop controller, use the theme-aware
        // solid background on RootGrid for a consistent look on every theme.

        ApplyLanguage();
        RebuildThemeCombo(AppSettings.Current.ThemeMode);
        SelectTheme(AppSettings.Current.ThemeMode);
        ShowPage("test");
        VersionText.Text = $"v{GetInformationalVersion()}";
    }

    private void ApplyTaskbarIcon(string iconPath)
    {
        try
        {
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
            _windowIcon = LoadImage(
                IntPtr.Zero,
                iconPath,
                1, // IMAGE_ICON
                0,
                0,
                0x10); // LR_LOADFROMFILE
            if (_windowIcon != 0)
            {
                SendMessage(hwnd, 0x0080, (nint)1, _windowIcon); // WM_SETICON ICON_BIG
                SendMessage(hwnd, 0x0080, (nint)0, _windowIcon); // WM_SETICON ICON_SMALL
            }
        }
        catch (Exception exc)
        {
            AppLog.Error("MainWindow taskbar icon failed: " + exc.Message);
        }
    }

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern nint LoadImage(
        nint hInstance, string name, uint type, int cx, int cy, uint fuLoad);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern nint SendMessage(
        nint hwnd, uint msg, nint wParam, nint lParam);

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
        FooterPanel.Visibility = NavView.IsPaneOpen ? Visibility.Visible : Visibility.Collapsed;
    }

    private void NavView_PaneOpened(NavigationView sender, object args) =>
        FooterPanel.Visibility = Visibility.Visible;

    private void NavView_PaneClosed(NavigationView sender, object args) =>
        FooterPanel.Visibility = Visibility.Collapsed;

    private void NavView_SelectionChanged(
        NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItem is NavigationViewItem { Tag: string tag })
        {
            AppLog.UserAction("open_page_" + tag);
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
            "debug" => typeof(DebugPage),
            "advanced" => typeof(AdvancedPage),
            _ => typeof(TestPage),
        };

        if (!_pages.TryGetValue(tag, out var page))
        {
            page = (Page)Activator.CreateInstance(type)!;
            _pages[tag] = page;
            if (page is TestPage testPage)
            {
                testPage.AttachWindow(this);
            }
            else if (page is AdvancedPage advancedPage)
            {
                advancedPage.AttachWindow(this);
            }
            else if (page is NexusPage nexusPage)
            {
                nexusPage.AttachWindow(this);
            }
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
        var elementTheme = mode switch
        {
            "light" => ElementTheme.Light,
            "dark" => ElementTheme.Dark,
            _ => ElementTheme.Default,
        };
        RootGrid.RequestedTheme = elementTheme;
        NavView.RequestedTheme = elementTheme;
        AppTitleBar.RequestedTheme = elementTheme;

        var isDark = RootGrid.ActualTheme == ElementTheme.Dark;
        var captionForeground = isDark ? Microsoft.UI.Colors.White : Microsoft.UI.Colors.Black;
        AppWindow.TitleBar.ButtonForegroundColor = captionForeground;
        AppWindow.TitleBar.ButtonInactiveForegroundColor = captionForeground;
    }

    private void LangEnButton_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("language_english");
        SetLanguage(Localizer.English);
        ApplyLanguage();
    }

    private void LangZhButton_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("language_chinese");
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
        TitleHelpButton.Content = Localizer.T("TitleBar.Help");
        TitleAboutButton.Content = Localizer.T("TitleBar.About");
        NavTestItem.Content = Localizer.T("Nav.Test");
        NavNexusItem.Content = Localizer.T("Nav.Nexus");
        NavBackupItem.Content = Localizer.T("Nav.Backup");
        NavQuarantineItem.Content = Localizer.T("Nav.Quarantine");
        NavDebugItem.Content = Localizer.T("Nav.Debug");
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

    private async void TitleHelpButton_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("open_help");
        var body = new TextBlock
        {
            Text = HelpTutorial.For(Localizer.CurrentLanguage),
            TextWrapping = TextWrapping.Wrap,
            LineHeight = 22,
        };
        var scroll = new ScrollViewer
        {
            Content = body,
            MaxHeight = 460,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
        };
        var dialog = new ContentDialog
        {
            Title = Localizer.T("Help.Title"),
            Content = scroll,
            CloseButtonText = Localizer.T("Help.Close"),
            DefaultButton = ContentDialogButton.Close,
            XamlRoot = RootGrid.XamlRoot,
        };
        await ShowExclusiveDialogAsync(dialog);
    }

    private async void TitleAboutButton_Click(object sender, RoutedEventArgs e)
    {
        AppLog.UserAction("open_about");

        var heading = new TextBlock
        {
            Text = $"RoNCT v{GetInformationalVersion()}",
            Style = (Style)Application.Current.Resources["SubtitleTextBlockStyle"],
            FontWeight = Microsoft.UI.Text.FontWeights.SemiBold,
        };
        var mailButton = new HyperlinkButton
        {
            Content = ContactEmail,
            NavigateUri = new Uri($"mailto:{ContactEmail}"),
        };
        var githubButton = new HyperlinkButton
        {
            Content = Localizer.T("About.GitHub"),
            NavigateUri = new Uri(GitHubUrl),
        };
        var logo = new Image
        {
            Source = new BitmapImage(new Uri("ms-appx:///Assets/logo_meme.png")),
            Width = 320,
            HorizontalAlignment = HorizontalAlignment.Center,
            Margin = new Thickness(0, 0, 0, 8),
        };
        var content = new StackPanel
        {
            MinWidth = 380,
            Spacing = 4,
            Children =
            {
                logo,
                heading,
                new TextBlock
                {
                    Text = Localizer.T("About.Name"),
                    TextWrapping = TextWrapping.Wrap,
                    Opacity = 0.9,
                },
                new TextBlock
                {
                    Text = string.Format(Localizer.T("About.Author"), Author),
                    TextWrapping = TextWrapping.Wrap,
                    Opacity = 0.9,
                },
                new TextBlock
                {
                    Text = Localizer.T("About.Contact"),
                    Margin = new Thickness(0, 12, 0, 0),
                    Opacity = 0.7,
                },
                mailButton,
                githubButton,
                new TextBlock
                {
                    Text = string.Format(Localizer.T("About.License"), LicenseName),
                    Margin = new Thickness(0, 12, 0, 0),
                    TextWrapping = TextWrapping.Wrap,
                    Opacity = 0.7,
                },
            },
        };

        var dialog = new ContentDialog
        {
            Title = Localizer.T("About.Title"),
            Content = content,
            CloseButtonText = Localizer.T("About.Close"),
            DefaultButton = ContentDialogButton.Close,
            XamlRoot = RootGrid.XamlRoot,
        };
        await ShowExclusiveDialogAsync(dialog);
    }

    /// <summary>
    /// WinUI allows only one ContentDialog per XamlRoot at a time. This guard
    /// prevents two title-bar buttons from opening overlapping dialogs.
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

    /// <summary>
    /// Keeps the RoNCT window above other windows (for example while the API-key
    /// guide opens the browser) and releases it again afterwards.
    /// </summary>
    public void SetAlwaysOnTop(bool onTop)
    {
        try
        {
            if (AppWindow.Presenter is OverlappedPresenter presenter)
            {
                presenter.IsAlwaysOnTop = onTop;
            }
        }
        catch (Exception exc)
        {
            AppLog.Error("MainWindow SetAlwaysOnTop failed: " + exc.Message);
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
