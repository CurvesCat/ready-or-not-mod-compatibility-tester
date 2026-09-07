namespace RoNCT.App.Services;

/// <summary>
/// Windows-native folder / file pickers, initialized on the owning window so
/// they appear as a proper modal dialog for a WinUI 3 desktop app. Picker
/// dialogs can optionally be opened at a real start directory instead of the
/// generic Documents location that the Windows.Storage.Pickers projection uses.
/// </summary>
public static class WindowsPicker
{
    private static nint GetWindowHandle(Microsoft.UI.Xaml.Window window) =>
        WinRT.Interop.WindowNative.GetWindowHandle(window);

    public static Task<IReadOnlyList<string>> PickPakFilesAsync(
        Microsoft.UI.Xaml.Window window,
        string? initialDirectory = null) =>
        Task.FromResult(NativeFileDialog.PickPakFiles(
            GetWindowHandle(window), initialDirectory));

    public static Task<string?> PickFolderAsync(
        Microsoft.UI.Xaml.Window window,
        string? initialDirectory = null) =>
        Task.FromResult(NativeFileDialog.PickFolder(
            GetWindowHandle(window), initialDirectory));

    public static Task<string?> PickSingleFileAsync(
        Microsoft.UI.Xaml.Window window,
        IReadOnlyList<string> extensions,
        string? initialDirectory = null)
    {
        var selected = NativeFileDialog.PickFile(
            GetWindowHandle(window), initialDirectory, extensions);
        return Task.FromResult(selected);
    }

    /// <summary>
    /// Picks the best existing directory to open a file dialog in. Returns
    /// <see langword="null"/> when nothing sensible exists so the shell keeps
    /// its own last-used location.
    /// </summary>
    public static string? ResolveStartDirectory(
        string? configuredFolder,
        IEnumerable<string> selectedFiles,
        string? gameRoot,
        IEnumerable<string> fallbackFolders)
    {
        var candidates = new List<string?>();

        if (!string.IsNullOrWhiteSpace(configuredFolder))
        {
            candidates.Add(configuredFolder);
        }

        foreach (var file in selectedFiles)
        {
            if (string.IsNullOrWhiteSpace(file))
            {
                continue;
            }
            var parent = Path.GetDirectoryName(file);
            if (!string.IsNullOrWhiteSpace(parent))
            {
                candidates.Add(parent);
                break;
            }
        }

        if (!string.IsNullOrWhiteSpace(gameRoot))
        {
            candidates.Add(Path.Combine(
                gameRoot, "ReadyOrNot", "Content", "Paks"));
        }

        foreach (var folder in fallbackFolders)
        {
            if (!string.IsNullOrWhiteSpace(folder))
            {
                candidates.Add(folder);
            }
        }

        foreach (var candidate in candidates)
        {
            if (candidate is not null && Directory.Exists(candidate))
            {
                return candidate;
            }
        }

        return null;
    }
}
