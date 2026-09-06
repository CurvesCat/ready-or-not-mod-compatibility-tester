using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class TestPage : Page, ILocalizablePage
{
    public TestPage()
    {
        InitializeComponent();
        ApplyLanguage();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Test");
        PageBodyText.Text = Localizer.T("Page.Test.Body");
    }
}
