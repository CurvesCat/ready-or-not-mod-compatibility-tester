using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class NexusPage : Page, ILocalizablePage
{
    public NexusPage()
    {
        InitializeComponent();
        ApplyLanguage();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Nexus");
        PageBodyText.Text = Localizer.T("Page.Nexus.Body");
    }
}
