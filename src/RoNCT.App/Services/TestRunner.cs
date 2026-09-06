using RoNCT.Core.Configuration;
using RoNCT.Core.Plan;
using RoNCT.Core.Reporting;
using RoNCT.Core.Scan;
using RoNCT.Core.Selection;

namespace RoNCT.App.Services;

public sealed class GroupOutcome
{
    public GroupOutcome(string label, IReadOnlyList<string> mods, SessionResult result)
    {
        Label = label;
        Mods = mods;
        Result = result;
    }

    public string Label { get; }
    public IReadOnlyList<string> Mods { get; }
    public SessionResult Result { get; }
}

public sealed class TestRunResult
{
    public TestRunResult(IReadOnlyList<GroupOutcome> outcomes, string? jsonReport, string? csvReport)
    {
        Outcomes = outcomes;
        JsonReport = jsonReport;
        CsvReport = csvReport;
    }

    public IReadOnlyList<GroupOutcome> Outcomes { get; }
    public string? JsonReport { get; }
    public string? CsvReport { get; }
}

public static class TestRunner
{
    public static async Task<TestRunResult> RunAsync(
        AppConfig config,
        IReadOnlyList<ModItem> mods,
        Action<string> emit,
        CancellationToken cancellationToken)
    {
        var exePath = config.ExePath;
        var gameRoot = config.GameRoot;
        var knownExe =
            @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Binaries\Win64\ReadyOrNotSteam-Win64-Shipping.exe";
        var knownRoot =
            @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not";
        if (string.IsNullOrEmpty(exePath) || !File.Exists(exePath))
        {
            if (File.Exists(knownExe))
            {
                exePath = knownExe;
                config.ExePath = knownExe;
                AppSettings.Save();
            }
        }
        if (string.IsNullOrEmpty(gameRoot))
        {
            if (Directory.Exists(knownRoot))
            {
                gameRoot = knownRoot;
                config.GameRoot = knownRoot;
                AppSettings.Save();
            }
        }
        if (string.IsNullOrEmpty(exePath) || !File.Exists(exePath))
        {
            throw new InvalidOperationException("Game executable path is not set or does not exist.");
        }

        var gameModDir = ResolveGameModDir(config, gameRoot ?? string.Empty);
        var logDir = Path.Combine(AppSettings.DataDirectory, "logs");
        var reportDir = string.IsNullOrEmpty(config.ReportDir)
            ? Path.Combine(AppSettings.DataDirectory, "reports")
            : config.ReportDir;
        var crashesDir = ResolveCrashesDir(config);

        // Build plan from static name conflicts (dependency edges + rules come later).
        var conflicts = ConflictScanner.FindConflicts(mods);
        var scanned = mods.Select(mod => mod.FileName).ToList();
        var conflictPairs = conflicts
            .Select(c => (IReadOnlyList<string>)new[] { c.A.FileName, c.B.FileName })
            .ToList();
        var plan = DeploymentPlanner.Build(scanned, conflictPairs, Array.Empty<DependencyEdge>());

        emit($"Planned {plan.Groups.Count} test group(s).");
        var outcomes = new List<GroupOutcome>();
        var groupIndex = 0;
        foreach (var group in plan.Groups)
        {
            if (cancellationToken.IsCancellationRequested)
            {
                outcomeSkipped(outcomes, group);
                break;
            }
            groupIndex++;

            var groupMods = mods
                .Where(mod => group.Mods.Contains(mod.FileName, StringComparer.OrdinalIgnoreCase))
                .ToList();
            var deployItems = groupMods
                .Where(mod => !IsInside(mod.FilePath, gameModDir))
                .Select(mod => new DeploySource(mod.FilePath, mod.FileName))
                .ToList();

            emit($"Testing group {groupIndex}/{plan.Groups.Count} ({group.Reason})...");
            var session = new GameSession(
                exePath,
                gameModDir,
                logDir,
                crashesDir,
                config.StableSeconds,
                config.StartupTimeoutSeconds,
                config.MenuHoldSeconds,
                config.ExtraArgs,
                emit,
                cancellationToken);
            var result = await Task.Run(
                () => session.Run(deployItems, $"group_{groupIndex}"),
                cancellationToken);
            outcomes.Add(new GroupOutcome($"g{groupIndex}", group.Mods, result));
        }

        var jsonReport = ReportWriter.WriteJson(
            reportDir, "mod_compat_report", new
            {
                created_at = DateTime.Now.ToString("s"),
                groups = outcomes.Select(o => new
                {
                    label = o.Label,
                    mods = o.Mods,
                    verdict = o.Result.Verdict.ToString(),
                    reason = o.Result.Reason,
                    elapsed_seconds = o.Result.ElapsedSeconds,
                }),
            });

        var csvRows = new List<IReadOnlyList<string>>
        {
            new[] { "group", "mod", "verdict", "reason", "elapsed_seconds" },
        };
        foreach (var outcome in outcomes)
        {
            foreach (var modName in outcome.Mods)
            {
                csvRows.Add(new[]
                {
                    outcome.Label, modName, outcome.Result.Verdict.ToString(),
                    outcome.Result.Reason, outcome.Result.ElapsedSeconds.ToString("0.00"),
                });
            }
        }
        var csvReport = ReportWriter.WriteCsv(reportDir, "mod_compat_report", csvRows);

        return new TestRunResult(outcomes, jsonReport, csvReport);
    }

    private static void outcomeSkipped(List<GroupOutcome> outcomes, DeployGroup group)
    {
        outcomes.Add(new GroupOutcome(group.GroupId, group.Mods,
            new SessionResult(TestVerdict.Skipped, "Cancelled", string.Empty, false, 0, Array.Empty<string>())));
    }

    private static string ResolveGameModDir(AppConfig config, string gameRoot)
    {
        if (!string.IsNullOrEmpty(config.ModFolder) && Directory.Exists(config.ModFolder))
        {
            return config.ModFolder;
        }
        if (!string.IsNullOrEmpty(gameRoot))
        {
            var candidate = Path.Combine(gameRoot, "ReadyOrNot", "Content", "Paks");
            if (Directory.Exists(candidate))
            {
                return candidate;
            }
        }
        return @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Content\Paks";
    }

    private static string? ResolveCrashesDir(AppConfig config)
    {
        if (string.IsNullOrEmpty(config.GameRoot))
        {
            return null;
        }
        var candidates = new[]
        {
            Path.Combine(config.GameRoot, "ReadyOrNot", "Saved", "CrashReports"),
            Path.Combine(config.GameRoot, "ReadyOrNot", "Binaries", "Win64", "CrashReports"),
        };
        return candidates.FirstOrDefault(Directory.Exists);
    }

    private static bool IsInside(string filePath, string folder) =>
        Path.GetFullPath(filePath).StartsWith(
            Path.GetFullPath(folder), StringComparison.OrdinalIgnoreCase);
}
