using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class AdvancedPage : Page, ILocalizablePage
{
    public AdvancedPage()
    {
        InitializeComponent();
        ApplyLanguage();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Advanced");
        PageBodyText.Text = Localizer.T("Page.Advanced.Body");
    }
}
