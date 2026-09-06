using System.Diagnostics;
using System.Text.Json;

namespace RoNCT.App.Services;

public sealed class UAssetJson
{
    public List<UAssetImport>? Imports { get; set; }
    public List<string>? SoftPackageReferenceList { get; set; }
}

public sealed class UAssetImport
{
    public string? ObjectName { get; set; }
}

public static class UAssetCliService
{
    public static async Task<UAssetJson?> ToJsonAsync(
        string dotnetExe,
        string uassetCliDll,
        string uassetPath,
        string? uexpPath,
        string engine,
        CancellationToken cancellationToken = default)
    {
        var tempRoot = Path.Combine(
            Path.GetTempPath(), "ronct-dep-assets", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempRoot);

        try
        {
            var extension = Path.GetExtension(uassetPath);
            var fileName = Path.GetFileNameWithoutExtension(uassetPath);
            var assetCopy = Path.Combine(tempRoot, fileName + extension);
            File.Copy(uassetPath, assetCopy, overwrite: true);
            if (uexpPath is not null && File.Exists(uexpPath))
            {
                File.Copy(uexpPath, Path.Combine(tempRoot, fileName + ".uexp"), overwrite: true);
            }

            var jsonPath = Path.Combine(tempRoot, fileName + ".json");
            var startInfo = new ProcessStartInfo(dotnetExe)
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };
            startInfo.ArgumentList.Add(uassetCliDll);
            startInfo.ArgumentList.Add("tojson");
            startInfo.ArgumentList.Add(assetCopy);
            startInfo.ArgumentList.Add(jsonPath);
            startInfo.ArgumentList.Add(engine);

            using var process = Process.Start(startInfo);
            if (process is null)
            {
                return null;
            }
            await process.WaitForExitAsync(cancellationToken);
            if (process.ExitCode != 0 || !File.Exists(jsonPath))
            {
                return null;
            }

            return JsonSerializer.Deserialize<UAssetJson>(
                await File.ReadAllTextAsync(jsonPath, cancellationToken));
        }
        finally
        {
            try { Directory.Delete(tempRoot, recursive: true); }
            catch { /* best effort */ }
        }
    }
}
