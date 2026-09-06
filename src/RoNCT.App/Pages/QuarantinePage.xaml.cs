using Microsoft.UI.Xaml.Controls;
using RoNCT.App.Services;

namespace RoNCT.App.Pages;

public sealed partial class QuarantinePage : Page, ILocalizablePage
{
    public QuarantinePage()
    {
        InitializeComponent();
        ApplyLanguage();
    }

    public void ApplyLanguage()
    {
        PageTitle.Text = Localizer.T("Nav.Quarantine");
        PageBodyText.Text = Localizer.T("Page.Quarantine.Body");
    }
}
