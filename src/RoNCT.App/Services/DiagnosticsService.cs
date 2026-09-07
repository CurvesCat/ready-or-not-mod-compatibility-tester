using System.Runtime.InteropServices;
using RoNCT.Core.Configuration;

namespace RoNCT.App.Services;

/// <summary>
/// Builds a support-ready diagnostic snapshot without leaking secrets such as
/// the Nexus API key. Users can copy this text when reporting a bug.
/// </summary>
public static class DiagnosticsService
{
    public static string Collect(AppConfig config)
    {
        var builder = new System.Text.StringBuilder();
        builder.AppendLine("RoNCT diagnostic report");
        builder.AppendLine("-----------------------");
        builder.AppendLine("Version: " + AppVersion());
        builder.AppendLine("OS: " + RuntimeInformation.OSDescription);
        builder.AppendLine("Architecture: " + RuntimeInformation.OSArchitecture);
        builder.AppendLine("Data directory: " + AppSettings.DataDirectory);
        builder.AppendLine();
        builder.AppendLine("Settings (API key hidden):");
        builder.AppendLine($"  Language: {config.Language}");
        builder.AppendLine($"  Theme: {config.ThemeMode}");
        builder.AppendLine($"  Mod folder: {Describe(config.ModFolder)}");
        builder.AppendLine($"  Selected pak files: {config.SelectedPakFiles.Count}");
        builder.AppendLine($"  Game root: {Describe(config.GameRoot)}");
        builder.AppendLine($"  Exe path: {Describe(config.ExePath)}");
        builder.AppendLine($"  Report dir: {Describe(config.ReportDir)}");
        builder.AppendLine($"  Backup dir: {Describe(config.BackupDir)}");
        builder.AppendLine($"  Quarantine dir: {Describe(config.QuarantineDir)}");
        builder.AppendLine($"  Repak: {Describe(config.RepakExe)}");
        builder.AppendLine($"  Dotnet: {Describe(config.DotnetExe)}");
        builder.AppendLine($"  UAssetCLI: {Describe(config.UAssetCliDll)}");
        builder.AppendLine($"  Engine: {config.Engine}");
        builder.AppendLine($"  Asset limit: {config.AssetLimit}");
        builder.AppendLine($"  Analyze dependencies: {config.AnalyzeDeps}");
        builder.AppendLine($"  Auto calibrate: {config.AutoCalibrate}");
        builder.AppendLine();
        builder.AppendLine("Log file: " + AppLog.LogFile);
        builder.AppendLine();

        try
        {
            if (File.Exists(AppLog.LogFile))
            {
                var lines = File.ReadAllLines(AppLog.LogFile);
                var tail = lines.Skip(Math.Max(0, lines.Length - 400));
                builder.AppendLine("Last log lines (up to 400):");
                builder.AppendLine("----------------------------");
                foreach (var line in tail)
                {
                    builder.AppendLine(line);
                }
            }
            else
            {
                builder.AppendLine("No log file exists yet.");
            }
        }
        catch (Exception exc)
        {
            builder.AppendLine("Could not read log file: " + exc.Message);
        }

        return builder.ToString();
    }

    private static string AppVersion()
    {
        var assembly = typeof(DiagnosticsService).Assembly;
        var attribute = assembly
            .GetCustomAttributes(typeof(System.Reflection.AssemblyInformationalVersionAttribute), false)
            .OfType<System.Reflection.AssemblyInformationalVersionAttribute>()
            .FirstOrDefault();
        var raw = attribute?.InformationalVersion
            ?? assembly.GetName().Version?.ToString()
            ?? "unknown";
        return raw.Split('+')[0];
    }

    private static string Describe(string? value) =>
        string.IsNullOrWhiteSpace(value) ? "(empty)" : value;
}
