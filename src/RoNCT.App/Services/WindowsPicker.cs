using Windows.Storage.Pickers;

namespace RoNCT.App.Services;

/// <summary>
/// Windows-native folder / file pickers, initialized on the owning window so
/// they appear as a proper modal dialog for a WinUI 3 desktop app.
/// </summary>
public static class WindowsPicker
{
    private static nint GetWindowHandle(Microsoft.UI.Xaml.Window window) =>
        WinRT.Interop.WindowNative.GetWindowHandle(window);

    public static async Task<IReadOnlyList<string>> PickPakFilesAsync(
        Microsoft.UI.Xaml.Window window)
    {
        var picker = new FileOpenPicker();
        picker.FileTypeFilter.Add(".pak");
        WinRT.Interop.InitializeWithWindow.Initialize(picker, GetWindowHandle(window));

        var files = await picker.PickMultipleFilesAsync();
        return files.Select(file => file.Path).ToList();
    }

    public static async Task<string?> PickFolderAsync(Microsoft.UI.Xaml.Window window)
    {
        var picker = new FolderPicker();
        picker.FileTypeFilter.Add("*");
        WinRT.Interop.InitializeWithWindow.Initialize(picker, GetWindowHandle(window));

        var folder = await picker.PickSingleFolderAsync();
        return folder?.Path;
    }

    public static async Task<string?> PickSingleFileAsync(
        Microsoft.UI.Xaml.Window window,
        IReadOnlyList<string> extensions)
    {
        var picker = new FileOpenPicker();
        foreach (var extension in extensions)
        {
            picker.FileTypeFilter.Add(extension);
        }
        WinRT.Interop.InitializeWithWindow.Initialize(picker, GetWindowHandle(window));

        var file = await picker.PickSingleFileAsync();
        return file?.Path;
    }
}
