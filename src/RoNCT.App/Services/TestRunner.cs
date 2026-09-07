using RoNCT.Analysis;
using RoNCT.Core.Configuration;
using RoNCT.Core.Deployment;
using RoNCT.Core.Plan;
using RoNCT.Core.Reporting;
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
    public TestRunResult(
        IReadOnlyList<GroupOutcome> outcomes,
        string? jsonReport,
        string? csvReport,
        IReadOnlyList<DeployGroup>? groups = null,
        string? backupDir = null,
        string? quarantineDir = null)
    {
        Outcomes = outcomes;
        JsonReport = jsonReport;
        CsvReport = csvReport;
        Groups = groups ?? Array.Empty<DeployGroup>();
        BackupDir = backupDir;
        QuarantineDir = quarantineDir;
    }

    public IReadOnlyList<GroupOutcome> Outcomes { get; }
    public string? JsonReport { get; }
    public string? CsvReport { get; }
    public IReadOnlyList<DeployGroup> Groups { get; }
    public string? BackupDir { get; }
    public string? QuarantineDir { get; }
}

public static class TestRunner
{
    private static readonly string KnownExe =
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not\ReadyOrNot\Binaries\Win64\ReadyOrNotSteam-Win64-Shipping.exe";

    private static readonly string KnownRoot =
        @"C:\Program Files (x86)\Steam\steamapps\common\Ready Or Not";

    public static async Task<TestRunResult> RunAsync(
        AppConfig config,
        IReadOnlyList<ModItem> mods,
        Action<string> emit,
        CancellationToken cancellationToken)
    {
        var exePath = ResolveExePath(config);
        var gameRoot = ResolveGameRoot(config);
        var gameModDir = ResolveGameModDir(config, gameRoot);

        var logDir = Path.Combine(AppSettings.DataDirectory, "logs");
        var reportDir = string.IsNullOrEmpty(config.ReportDir)
            ? Path.Combine(AppSettings.DataDirectory, "reports")
            : config.ReportDir;
        var crashesDir = ResolveCrashesDir(config);
        var sessionBase = Path.Combine(
            AppSettings.DataDirectory,
            "sessions",
            $"run_{DateTime.Now:yyyyMMdd-HHmmss}_{Guid.NewGuid():N}");
        Directory.CreateDirectory(sessionBase);
        var quarantineDir = string.IsNullOrEmpty(config.QuarantineDir)
            ? Path.Combine(AppSettings.DataDirectory, "quarantine")
            : config.QuarantineDir;

        Directory.CreateDirectory(logDir);
        AppLog.Log($"TestRunner: starting with {mods.Count} mod(s); autoCalibrate={config.AutoCalibrate}");

        if (config.CloseRunning)
        {
            var running = GameProcessService.FindGameProcessIds(exePath);
            if (running.Count > 0)
            {
                emit("Closing the running game before testing...");
                GameProcessService.GracefulClose(running, timeoutSeconds: 20);
            }
        }

        var before = BackupService.SnapshotModDir(gameModDir);
        string? backupDir = null;
        if (config.BackupEnabled)
        {
            var backupRoot = string.IsNullOrEmpty(config.BackupDir)
                ? Path.Combine(AppSettings.DataDirectory, "backup")
                : config.BackupDir;
            var (createdBackup, manifestPath) = BackupService.CreateBackup(
                gameModDir,
                backupRoot,
                backupEnabled: true,
                config.BackupMaxFileMb * 1024 * 1024,
                config.BackupMaxTotalMb * 1024 * 1024);
            backupDir = createdBackup;
            emit($"Backup created: {manifestPath}");
        }

        if (config.AutoCalibrate)
        {
            emit("Auto-calibrating startup timing (launches the game once)...");
            var cal = CalibrationService.Run(
                exePath,
                config.ExtraArgs,
                logDir,
                config.StartupTimeoutSeconds,
                120,
                emit,
                cancellationToken);
            config.StableSeconds = cal.SuggestedStable;
            AppSettings.Save();
            emit(
                $"Calibration done: window={cal.WindowSeconds:0.0}s, " +
                $"menu={cal.MenuSeconds:0.0}s -> stable {cal.SuggestedStable:0}s");
        }

        var byName = new Dictionary<string, List<ModItem>>(StringComparer.OrdinalIgnoreCase);
        foreach (var mod in mods)
        {
            if (!byName.TryGetValue(mod.FileName, out var list))
            {
                list = new List<ModItem>();
                byName[mod.FileName] = list;
            }
            list.Add(mod);
        }

        var plan = await BuildPlanAsync(
            config, mods, byName, emit, cancellationToken);
        emit(
            $"Planned {plan.Groups.Count} test group(s) " +
            $"({plan.ConflictPairs.Count} conflict pair(s)).");
        foreach (var warning in plan.Warnings)
        {
            emit("Warning: " + warning);
        }
        AppLog.Log(
            $"TestRunner: plan groups={plan.Groups.Count} " +
            $"conflicts={plan.ConflictPairs.Count} warnings={plan.Warnings.Count}");

        var outcomes = new List<GroupOutcome>();
        var installedNames = new ModFolderOperator(gameModDir, sessionBase).InstalledModNames();

        try
        {
            await ExecutePlanAsync(
                plan,
                byName,
                exePath,
                gameModDir,
                logDir,
                crashesDir,
                sessionBase,
                quarantineDir,
                config,
                outcomes,
                emit,
                cancellationToken);
        }
        finally
        {
            var disposed = ApplyInstalledDisposition(
                outcomes,
                config.Disposition,
                installedNames,
                gameModDir,
                quarantineDir,
                emit);
            var diffs = BackupService.VerifyDirState(gameModDir, before)
                .Where(diff => !disposed.Contains(Path.GetFileName(diff.Split(':')[1].Trim())))
                .ToArray();
            if (diffs.Length > 0)
            {
                emit("Warning: Mod directory state changed during the run:");
                foreach (var diff in diffs)
                {
                    emit("  - " + diff);
                }
                AppLog.Log("TestRunner: mod dir verification diffs: " + string.Join(" | ", diffs));
            }
            else
            {
                emit("Mod directory state verified; no unexpected changes.");
            }

            if (!TryDeleteSessionBase(sessionBase, emit))
            {
                emit(
                    "WARNING: parked mod files remain under " + sessionBase +
                    ". Move them back into the game Mod folder before launching the game.");
            }
        }

        var jsonReport = ReportWriter.WriteJson(
            reportDir,
            "mod_compat_report",
            new
            {
                created_at = DateTime.Now.ToString("s"),
                plan = plan.Groups.Select(group => new
                {
                    id = group.GroupId,
                    mods = group.Mods,
                    reason = group.Reason,
                    evidence = group.Evidence,
                }),
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
        AppLog.Log($"TestRunner: finished, reports at {jsonReport}");

        return new TestRunResult(outcomes, jsonReport, csvReport, plan.Groups, backupDir, quarantineDir);
    }

    private static async Task<DeployPlan> BuildPlanAsync(
        AppConfig config,
        IReadOnlyList<ModItem> mods,
        IReadOnlyDictionary<string, List<ModItem>> byName,
        Action<string> emit,
        CancellationToken cancellationToken)
    {
        var names = mods.Select(mod => mod.FileName).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        if (!config.AnalyzeDeps)
        {
            return DeploymentPlanner.Build(
                names,
                Array.Empty<IReadOnlyList<string>>(),
                Array.Empty<DependencyEdge>());
        }

        emit("Analyzing asset dependencies before grouping (no game launch)...");
        using var session = new Cue4AnalysisSession();
        var graph = await DependencyScanner.ScanGraphAsync(
            repakExe: null,
            dotnetExe: null,
            uassetCliDll: null,
            string.IsNullOrEmpty(config.Engine) ? "VER_UE5_4" : config.Engine,
            mods,
            config.AssetLimit > 0 ? config.AssetLimit : 0,
            cancellationToken,
            session,
            session,
            new Cue4AssetParser());
        emit(
            $"Dependency analysis done: {graph.Paks} pak(s), {graph.ParsedAssets} asset(s), " +
            $"{graph.Edges.Count} cross-mod edge(s), {graph.Unresolved} unresolved reference(s).");
        return DeploymentPlanner.Build(
            names,
            graph.ConflictPairs,
            graph.Edges);
    }

    private static async Task ExecutePlanAsync(
        DeployPlan plan,
        IReadOnlyDictionary<string, List<ModItem>> byName,
        string exePath,
        string gameModDir,
        string logDir,
        string? crashesDir,
        string sessionBase,
        string quarantineDir,
        AppConfig config,
        List<GroupOutcome> outcomes,
        Action<string> emit,
        CancellationToken cancellationToken)
    {
        var groupIndex = 0;
        foreach (var group in plan.Groups)
        {
            groupIndex++;
            var label = $"g{groupIndex}";
            var items = group.Mods
                .Where(name => byName.ContainsKey(name))
                .SelectMany(name => byName[name])
                .ToList();
            var missing = group.Mods.Where(name => !byName.ContainsKey(name)).ToArray();
            if (missing.Length > 0)
            {
                emit($"Group {label} skipped missing files: {string.Join(", ", missing)}");
            }
            if (items.Count == 0)
            {
                continue;
            }
            if (cancellationToken.IsCancellationRequested)
            {
                outcomes.Add(SkippedOutcome(
                    label,
                    items.Select(item => item.FileName).ToArray()));
                break;
            }

            emit(
                $"Testing group {groupIndex}/{plan.Groups.Count} " +
                $"({group.Reason}): {string.Join(", ", items.Select(item => item.FileName))}");
            var result = await RunConfigurationAsync(
                items,
                label,
                exePath,
                gameModDir,
                logDir,
                crashesDir,
                sessionBase,
                config,
                emit,
                cancellationToken);
            AppLog.Log($"Group {label} verdict={result.Verdict}: {result.Reason}");

            if (result.Verdict == TestVerdict.Fail && items.Count > 1)
            {
                emit(
                    $"Group {label} failed with {items.Count} mods; " +
                    "retesting each mod alone to attribute the failure.");
                var fallbackIndex = 0;
                foreach (var item in items)
                {
                    if (cancellationToken.IsCancellationRequested)
                    {
                        outcomes.Add(SkippedOutcome(label, new[] { item.FileName }));
                        break;
                    }
                    fallbackIndex++;
                    var singleLabel = $"{label}-f{fallbackIndex}";
                    var single = await RunConfigurationAsync(
                        new[] { item },
                        singleLabel,
                        exePath,
                        gameModDir,
                        logDir,
                        crashesDir,
                        sessionBase,
                        config,
                        emit,
                        cancellationToken);
                    emit(
                        $"  {item.FileName} -> {single.Verdict}" +
                        (string.IsNullOrEmpty(single.Reason) ? string.Empty : $": {single.Reason}"));
                    outcomes.Add(new GroupOutcome(singleLabel, new[] { item.FileName }, single));
                }
            }
            else
            {
                outcomes.Add(new GroupOutcome(
                    label,
                    items.Select(item => item.FileName).ToArray(),
                    result));
            }
        }
    }

    private static async Task<SessionResult> RunConfigurationAsync(
        IReadOnlyList<ModItem> items,
        string label,
        string exePath,
        string gameModDir,
        string logDir,
        string? crashesDir,
        string sessionBase,
        AppConfig config,
        Action<string> emit,
        CancellationToken cancellationToken)
    {
        var safeLabel = SanitizeLabel(label);
        var groupDir = Path.Combine(sessionBase, safeLabel);
        var duplicateNames = items
            .GroupBy(item => item.FileName, StringComparer.OrdinalIgnoreCase)
            .Where(group => group.Count() > 1)
            .Select(group => group.Key)
            .ToArray();
        if (duplicateNames.Length > 0)
        {
            return new SessionResult(
                TestVerdict.Conflict,
                "Multiple selected files share the same name: " +
                string.Join(", ", duplicateNames),
                string.Empty,
                false,
                0,
                Array.Empty<string>());
        }
        var unavailable = items
            .Where(item => IsInside(item.FilePath, gameModDir) && !File.Exists(item.FilePath))
            .Select(item => item.FileName)
            .ToArray();
        if (unavailable.Length > 0)
        {
            return new SessionResult(
                TestVerdict.Error,
                "Selected installed mods no longer exist in the Mod folder: " +
                string.Join(", ", unavailable),
                string.Empty,
                false,
                0,
                Array.Empty<string>());
        }
        Directory.CreateDirectory(groupDir);
        var folderOperator = new ModFolderOperator(gameModDir, groupDir);
        var installedNow = folderOperator.InstalledModNames().ToHashSet(StringComparer.OrdinalIgnoreCase);
        var keep = items
            .Select(item => item.FileName)
            .Where(installedNow.Contains)
            .ToArray();
        var deployItems = items
            .Where(item => !IsInside(item.FilePath, gameModDir))
            .Select(item => new DeploySource(item.FilePath, item.FileName))
            .ToList();

        try
        {
            var parked = folderOperator.ParkOthers(keep);
            if (parked.Count > 0)
            {
                emit($"  Parked {parked.Count} other installed mod(s) for this group.");
            }

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
                () => session.Run(deployItems, safeLabel),
                cancellationToken);

            RemoveDeployed(deployItems, gameModDir);
            return result;
        }
        catch (Exception exc)
        {
            RemoveDeployed(deployItems, gameModDir);
            return new SessionResult(
                TestVerdict.Error,
                $"Session failed: {exc.Message}",
                string.Empty,
                false,
                0,
                Array.Empty<string>());
        }
        finally
        {
            try
            {
                folderOperator.RestoreAll();
            }
            catch (Exception exc)
            {
                emit($"  Could not restore parked mods after {label}: {exc.Message}");
                AppLog.Log($"TestRunner: restore failed for {label}: {exc}");
            }
            try
            {
                if (Directory.Exists(groupDir) &&
                    !Directory.EnumerateFileSystemEntries(groupDir).Any())
                {
                    Directory.Delete(groupDir);
                }
            }
            catch
            {
                // keep for manual inspection
            }
        }
    }

    private static HashSet<string> ApplyInstalledDisposition(
        IReadOnlyList<GroupOutcome> outcomes,
        string disposition,
        IReadOnlyCollection<string> installedNames,
        string gameModDir,
        string quarantineDir,
        Action<string> emit)
    {
        var handled = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (disposition != "quarantine" && disposition != "delete")
        {
            return handled;
        }

        foreach (var outcome in outcomes)
        {
            if (outcome.Result.Verdict is not (TestVerdict.Fail or TestVerdict.Error))
            {
                continue;
            }
            foreach (var modName in outcome.Mods)
            {
                if (outcome.Mods.Count != 1 ||
                    !installedNames.Contains(modName) ||
                    !BackupService.SafeBasename(modName))
                {
                    continue;
                }
                var source = Path.Combine(gameModDir, modName);
                if (!File.Exists(source))
                {
                    continue;
                }
                try
                {
                    if (disposition == "delete")
                    {
                        File.Delete(source);
                        emit($"  Removed unusable installed mod: {modName}");
                    }
                    else
                    {
                        Directory.CreateDirectory(quarantineDir);
                        var targetName = UniqueDestination(quarantineDir, modName);
                        File.Move(source, Path.Combine(quarantineDir, targetName));
                        emit($"  Moved unusable installed mod to quarantine: {targetName}");
                    }
                    handled.Add(modName);
                }
                catch (Exception exc)
                {
                    emit($"  Could not apply disposition to {modName}: {exc.Message}");
                }
            }
        }
        return handled;
    }

    private static GroupOutcome SkippedOutcome(string label, IReadOnlyList<string> mods) =>
        new(
            label,
            mods,
            new SessionResult(
                TestVerdict.Skipped,
                "Cancelled",
                string.Empty,
                false,
                0,
                Array.Empty<string>()));

    private static void RemoveDeployed(IEnumerable<DeploySource> items, string gameModDir)
    {
        foreach (var item in items)
        {
            try
            {
                var target = Path.Combine(gameModDir, item.TargetName);
                if (File.Exists(target))
                {
                    File.Delete(target);
                }
            }
            catch
            {
                // best effort; GameSession already cleans its own copies
            }
        }
    }

    private static bool TryDeleteSessionBase(string sessionBase, Action<string> emit)
    {
        if (!Directory.Exists(sessionBase))
        {
            return true;
        }
        var leftovers = Directory
            .EnumerateFiles(sessionBase, "*.pak", SearchOption.AllDirectories)
            .ToArray();
        if (leftovers.Length > 0)
        {
            emit($"  Leftover parked file(s): {string.Join(", ", leftovers.Select(Path.GetFileName))}");
            return false;
        }
        try
        {
            Directory.Delete(sessionBase, recursive: true);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static string UniqueDestination(string directory, string fileName)
    {
        var candidate = Path.Combine(directory, fileName);
        if (!File.Exists(candidate))
        {
            return fileName;
        }
        var stem = Path.GetFileNameWithoutExtension(fileName);
        var extension = Path.GetExtension(fileName);
        for (var counter = 2; ; counter++)
        {
            var name = $"{stem}_{counter}{extension}";
            if (!File.Exists(Path.Combine(directory, name)))
            {
                return name;
            }
        }
    }

    private static string SanitizeLabel(string label) =>
        string.Concat(label.Where(char.IsLetterOrDigit)).ToLowerInvariant();

    private static string ResolveExePath(AppConfig config)
    {
        if (!string.IsNullOrEmpty(config.ExePath) && File.Exists(config.ExePath))
        {
            return config.ExePath;
        }
        if (File.Exists(KnownExe))
        {
            config.ExePath = KnownExe;
            AppSettings.Save();
            return KnownExe;
        }
        throw new InvalidOperationException("Game executable path is not set or does not exist.");
    }

    private static string ResolveGameRoot(AppConfig config)
    {
        if (!string.IsNullOrEmpty(config.GameRoot) && Directory.Exists(config.GameRoot))
        {
            return config.GameRoot;
        }
        if (Directory.Exists(KnownRoot))
        {
            config.GameRoot = KnownRoot;
            AppSettings.Save();
            return KnownRoot;
        }
        return string.Empty;
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
        return KnownRoot + @"\ReadyOrNot\Content\Paks";
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
