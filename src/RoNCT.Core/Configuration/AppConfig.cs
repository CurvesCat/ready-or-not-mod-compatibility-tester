namespace RoNCT.Core.Configuration;

public sealed class AppConfig
{
    public string Language { get; set; } = "en";
    public string ThemeMode { get; set; } = "system";
    public string NexusApiKey { get; set; } = string.Empty;

    // Selection
    public string ModFolder { get; set; } = string.Empty;
    public List<string> SelectedPakFiles { get; set; } = new();

    // Game
    public string GameRoot { get; set; } = string.Empty;
    public string ExePath { get; set; } = string.Empty;
    public string ExtraArgs { get; set; } = "-windowed -nosplash";
    public bool CloseRunning { get; set; } = true;
    public double StableSeconds { get; set; } = 35;
    public double StartupTimeoutSeconds { get; set; } = 120;
    public double MenuHoldSeconds { get; set; } = 6;
    public bool AutoCalibrate { get; set; } = true;
    public string Source { get; set; } = "folder";
    public string Disposition { get; set; } = "quarantine";
    public bool Warmup { get; set; }

    // Directories and backup
    public string ReportDir { get; set; } = string.Empty;
    public string QuarantineDir { get; set; } = string.Empty;
    public string BackupDir { get; set; } = string.Empty;
    public bool BackupEnabled { get; set; } = true;
    public long BackupMaxFileMb { get; set; } = 1500;
    public long BackupMaxTotalMb { get; set; } = 10000;
    public List<string> ExcludeFiles { get; set; } = new();

    // Analysis tools
    public string RepakExe { get; set; } = string.Empty;
    public string DotnetExe { get; set; } = string.Empty;
    public string UAssetCliDll { get; set; } = string.Empty;
    public int AssetLimit { get; set; } = 100;
    public int Workers { get; set; } = 4;
    public string Engine { get; set; } = "VER_UE5_4";
    public bool AnalyzeDeps { get; set; } = true;

    // Updates (endpoint empty until GitHub hosting is available)
    public string UpdateManifestUrl { get; set; } = string.Empty;
}
