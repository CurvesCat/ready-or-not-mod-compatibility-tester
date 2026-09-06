using System.Diagnostics;
using RoNCT.Core.Analysis;

namespace RoNCT.App.Services;

public static class PakLister
{
    public static async Task<IReadOnlyList<string>?> ListAssetsAsync(
        string repakExe,
        string pakPath,
        CancellationToken cancellationToken = default)
    {
        var startInfo = new ProcessStartInfo(repakExe)
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        startInfo.ArgumentList.Add("list");
        startInfo.ArgumentList.Add(pakPath);

        using var process = Process.Start(startInfo);
        if (process is null)
        {
            return null;
        }

        var stdout = await process.StandardOutput.ReadToEndAsync();
        await process.WaitForExitAsync(cancellationToken);
        return process.ExitCode == 0 ? RepakListParser.Parse(stdout) : null;
    }
}
