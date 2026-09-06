using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class BackupPage : Page, ILocalizablePage
{
    public BackupPage()
    {
        InitializeComponent();
        ApplyLanguage();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Backup");
        PageBodyText.Text = Localizer.T("Page.Backup.Body");
    }
}
