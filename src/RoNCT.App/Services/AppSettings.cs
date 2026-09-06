using RoNCT.Core.Configuration;

namespace RoNCT.App.Services;

/// <summary>
/// Loads and saves the application configuration next to the executable.
/// </summary>
public static class AppSettings
{
    public static string DataDirectory { get; } =
        Path.GetDirectoryName(Environment.ProcessPath) ?? AppContext.BaseDirectory;

    public static AppConfig Current { get; private set; } =
        ConfigStore.Load(DataDirectory);

    public static void Save()
    {
        ConfigStore.Save(Current, DataDirectory);
    }
}
