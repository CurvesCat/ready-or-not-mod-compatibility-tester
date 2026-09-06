# RoNCT Core Foundation Implementation Plan (Milestone 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the RoNCT C#/.NET 10 solution in the new repository and
deliver the first testable `RoNCT.Core` slice: fresh configuration persistence
and pak-file source resolution.

**Architecture:** Three projects are created now (`RoNCT.Core`,
`RoNCT.Tests`, plus a solution file); the WinUI 3 `RoNCT.App` and
`RoNCT.Services` projects arrive in later milestone plans. `RoNCT.Core` stays
pure .NET: models, JSON config persistence, and file listing only. Windows,
game, and UI concerns are deliberately excluded from this milestone.

**Tech Stack:** C# 13 / .NET 10 SDK, xUnit, `dotnet` CLI, `System.Text.Json`.

**Spec:** `../specs/2026-09-07-ronct-csharp-rewrite-design.md` (read with this
plan; §3 confirmed decisions and §4 feature inventory define the target).

## Global Constraints

- Repository root: `C:\Users\curve\Documents\Codex\2026-09-07\RoNCT`.
- Branch: `main`. Commits are made after every green test run.
- Target framework: `net10.0` only.
- No third-party runtime packages in this milestone besides xUnit (test-only).
- The design spec is English; commit messages and code identifiers are English.
- Runtime data (`config.json`, `reports/`, `cache/`, `backup/`, `quarantine/`,
  `logs/`) is never committed (already covered by `.gitignore`).
- License: PolyForm Noncommercial 1.0.0. No code in this milestone introduces a
  dependency with an incompatible license.

---

### Task 1: Install a user-local .NET 10 SDK

**Files:** none (machine environment)

**Interfaces:**
- Consumes: nothing.
- Produces: a working `dotnet` CLI on `PATH` for every later task.

- [ ] **Step 1: Install the SDK with the official script**

Run in PowerShell:

```powershell
$installDir = Join-Path $env:USERPROFILE '.dotnet'
$script = Join-Path $env:TEMP 'dotnet-install.ps1'
Invoke-WebRequest -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile $script
& $script -Channel 10.0 -Quality GA -InstallDir $installDir
$env:PATH = "$installDir;$env:PATH"
dotnet --list-sdks
```

Expected: at least one line starting with `10.0.` (for example
`10.0.100`). If a `10.0.x` SDK is already listed before running, skip this
task entirely.

- [ ] **Step 2: Verify the SDK on a fresh PowerShell session**

Run:

```powershell
dotnet --version
```

Expected: a `10.0.x` version string. If `dotnet` is not found in a new
terminal, add `%USERPROFILE%\.dotnet` to the user `PATH` environment variable
with `setx PATH "$env:USERPROFILE\.dotnet;$env:PATH"` and start a new shell.

### Task 2: Scaffold the solution, Core project, and test project

**Files:**
- Create: `RoNCT.sln`
- Create: `src/RoNCT.Core/RoNCT.Core.csproj`
- Create: `tests/RoNCT.Tests/RoNCT.Tests.csproj`

**Interfaces:**
- Consumes: Task 1 SDK.
- Produces: a solution that `dotnet build` and `dotnet test` accept, used by
  every later task.

- [ ] **Step 1: Run the scaffold commands**

```powershell
$root = 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT'
dotnet new sln -n RoNCT -o $root
dotnet new classlib -n RoNCT.Core -o (Join-Path $root 'src/RoNCT.Core') -f net10.0
dotnet new xunit -n RoNCT.Tests -o (Join-Path $root 'tests/RoNCT.Tests') -f net10.0
dotnet sln (Join-Path $root 'RoNCT.sln') add (Join-Path $root 'src/RoNCT.Core/RoNCT.Core.csproj') (Join-Path $root 'tests/RoNCT.Tests/RoNCT.Tests.csproj')
dotnet add (Join-Path $root 'tests/RoNCT.Tests/RoNCT.Tests.csproj') reference (Join-Path $root 'src/RoNCT.Core/RoNCT.Core.csproj')
```

Expected: command output ends with success and no errors.

- [ ] **Step 2: Verify build and template test**

Run:

```powershell
dotnet build (Join-Path $root 'RoNCT.sln')
dotnet test (Join-Path $root 'tests/RoNCT.Tests/RoNCT.Tests.csproj')
```

Expected: build succeeds; the template test passes.

- [ ] **Step 3: Commit**

```powershell
git add RoNCT.sln src/RoNCT.Core tests/RoNCT.Tests
git commit -m 'chore: scaffold RoNCT solution with Core and test projects'
```

### Task 3: Fresh configuration model and JSON persistence

**Files:**
- Delete: `src/RoNCT.Core/Class1.cs`
- Create: `src/RoNCT.Core/Configuration/AppConfig.cs`
- Create: `src/RoNCT.Core/Configuration/ConfigStore.cs`
- Delete: `tests/RoNCT.Tests/UnitTest1.cs`
- Create: `tests/RoNCT.Tests/Configuration/ConfigStoreTests.cs`

**Interfaces:**
- Consumes: Task 2 projects.
- Produces:
  - `sealed class AppConfig` with the property list below.
  - `static class ConfigStore` with
    `static AppConfig Load(string baseDir)` and
    `static void Save(AppConfig config, string baseDir)`.
  - Later milestone plans extend `AppConfig`; never rename existing
    properties after this task.

- [ ] **Step 1: Write the failing tests**

Remove the template files first:

```powershell
Remove-Item 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT\src\RoNCT.Core\Class1.cs'
Remove-Item 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT\tests\RoNCT.Tests\UnitTest1.cs'
```

`tests/RoNCT.Tests/Configuration/ConfigStoreTests.cs`:

```csharp
using Xunit;
using RoNCT.Core.Configuration;

namespace RoNCT.Tests.Configuration;

public sealed class ConfigStoreTests : IDisposable
{
    private readonly string _dir = Path.Combine(
        Path.GetTempPath(), "ronct-config-tests-" + Guid.NewGuid().ToString("N"));

    public ConfigStoreTests() => Directory.CreateDirectory(_dir);

    public void Dispose()
    {
        try { Directory.Delete(_dir, recursive: true); }
        catch { /* best effort cleanup */ }
    }

    [Fact]
    public void Load_WhenFileMissing_ReturnsDefaults()
    {
        var config = ConfigStore.Load(_dir);
        Assert.Equal("en", config.Language);
        Assert.Equal("system", config.ThemeMode);
        Assert.Empty(config.SelectedPakFiles);
    }

    [Fact]
    public void Load_WhenFileCorrupt_ReturnsDefaultsWithoutThrowing()
    {
        File.WriteAllText(Path.Combine(_dir, "config.json"), "{ not json");
        var config = ConfigStore.Load(_dir);
        Assert.Equal("en", config.Language);
    }

    [Fact]
    public void SaveAndLoad_RoundTripsValues()
    {
        var original = new AppConfig
        {
            Language = "zh",
            ThemeMode = "dark",
            NexusApiKey = "test-key",
            ModFolder = @"C:\mods",
            StableSeconds = 41,
        };

        ConfigStore.Save(original, _dir);

        var loaded = ConfigStore.Load(_dir);
        Assert.Equal("zh", loaded.Language);
        Assert.Equal("dark", loaded.ThemeMode);
        Assert.Equal("test-key", loaded.NexusApiKey);
        Assert.Equal(@"C:\mods", loaded.ModFolder);
        Assert.Equal(41, loaded.StableSeconds);
    }
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
dotnet test (Join-Path 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT' 'tests/RoNCT.Tests/RoNCT.Tests.csproj')
```

Expected: build fails because `RoNCT.Core.Configuration` does not exist yet.

- [ ] **Step 3: Implement `AppConfig`**

`src/RoNCT.Core/Configuration/AppConfig.cs`:

```csharp
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
```

- [ ] **Step 4: Implement `ConfigStore`**

`src/RoNCT.Core/Configuration/ConfigStore.cs`:

```csharp
using System.Text.Json;

namespace RoNCT.Core.Configuration;

public static class ConfigStore
{
    public const string FileName = "config.json";

    public static string ConfigPath(string baseDir) =>
        Path.Combine(baseDir, FileName);

    public static AppConfig Load(string baseDir)
    {
        var path = ConfigPath(baseDir);
        if (!File.Exists(path))
        {
            return new AppConfig();
        }

        try
        {
            return JsonSerializer.Deserialize<AppConfig>(
                File.ReadAllText(path)) ?? new AppConfig();
        }
        catch (JsonException)
        {
            return new AppConfig();
        }
    }

    public static void Save(AppConfig config, string baseDir)
    {
        Directory.CreateDirectory(baseDir);
        var json = JsonSerializer.Serialize(
            config, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(ConfigPath(baseDir), json);
    }
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```powershell
dotnet test (Join-Path 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT' 'tests/RoNCT.Tests/RoNCT.Tests.csproj')
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```powershell
git add -A
git commit -m 'feat(core): add fresh AppConfig schema with JSON persistence'
```

### Task 4: Pak-file source resolution

**Files:**
- Create: `src/RoNCT.Core/Selection/PakSource.cs`
- Create: `tests/RoNCT.Tests/Selection/PakSourceTests.cs`

**Interfaces:**
- Consumes: Task 3 (`AppConfig.ModFolder`, `AppConfig.SelectedPakFiles`).
- Produces:
  - `sealed record ModItem(string FilePath, string FileName, long SizeBytes)`.
  - `static class PakSource` with
    `static IReadOnlyList<ModItem> FromFolder(string folderPath)` and
    `static IReadOnlyList<ModItem> FromFiles(IEnumerable<string> filePaths)`.
  - Later plans use `ModItem` for scans, grouping, and reports.

- [ ] **Step 1: Write the failing tests**

`tests/RoNCT.Tests/Selection/PakSourceTests.cs`:

```csharp
using Xunit;
using RoNCT.Core.Selection;

namespace RoNCT.Tests.Selection;

public sealed class PakSourceTests : IDisposable
{
    private readonly string _dir = Path.Combine(
        Path.GetTempPath(), "ronct-paksource-tests-" + Guid.NewGuid().ToString("N"));

    public PakSourceTests() => Directory.CreateDirectory(_dir);

    public void Dispose()
    {
        try { Directory.Delete(_dir, recursive: true); }
        catch { /* best effort cleanup */ }
    }

    [Fact]
    public void FromFolder_ReturnsOnlyPakFilesSorted()
    {
        File.WriteAllText(Path.Combine(_dir, "b.pak"), string.Empty);
        File.WriteAllText(Path.Combine(_dir, "a.pak"), string.Empty);
        File.WriteAllText(Path.Combine(_dir, "notes.txt"), string.Empty);

        var items = PakSource.FromFolder(_dir);

        Assert.Equal(2, items.Count);
        Assert.Equal("a.pak", items[0].FileName);
        Assert.Equal("b.pak", items[1].FileName);
    }

    [Fact]
    public void FromFiles_KeepsExplicitOrderAndDropsMissingFiles()
    {
        var first = Path.Combine(_dir, "first.pak");
        var second = Path.Combine(_dir, "second.pak");
        File.WriteAllText(first, string.Empty);
        File.WriteAllText(second, string.Empty);

        var items = PakSource.FromFiles(new[] { second, first, Path.Combine(_dir, "missing.pak") });

        Assert.Equal(2, items.Count);
        Assert.Equal("second.pak", items[0].FileName);
        Assert.Equal("first.pak", items[1].FileName);
    }
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
dotnet test (Join-Path 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT' 'tests/RoNCT.Tests/RoNCT.Tests.csproj')
```

Expected: build fails because `RoNCT.Core.Selection` does not exist yet.

- [ ] **Step 3: Implement `PakSource`**

`src/RoNCT.Core/Selection/PakSource.cs`:

```csharp
namespace RoNCT.Core.Selection;

public sealed record ModItem(string FilePath, string FileName, long SizeBytes);

public static class PakSource
{
    public static IReadOnlyList<ModItem> FromFolder(string folderPath)
    {
        if (!Directory.Exists(folderPath))
        {
            return Array.Empty<ModItem>();
        }

        return Directory
            .EnumerateFiles(folderPath, "*.pak", SearchOption.TopDirectoryOnly)
            .OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase)
            .Select(ToItem)
            .ToArray();
    }

    public static IReadOnlyList<ModItem> FromFiles(IEnumerable<string> filePaths)
    {
        return filePaths
            .Where(File.Exists)
            .Where(path => string.Equals(
                Path.GetExtension(path), ".pak", StringComparison.OrdinalIgnoreCase))
            .Select(ToItem)
            .ToArray();
    }

    private static ModItem ToItem(string path)
    {
        var info = new FileInfo(path);
        return new ModItem(info.FullName, info.Name, info.Length);
    }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
dotnet test (Join-Path 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT' 'tests/RoNCT.Tests/RoNCT.Tests.csproj')
```

Expected: all 5 tests pass (3 config + 2 selection).

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m 'feat(core): add pak source resolution for folder and explicit files'
```

### Task 5: Milestone verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite from a clean build**

```powershell
dotnet clean (Join-Path 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT' 'RoNCT.sln')
dotnet build (Join-Path 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT' 'RoNCT.sln')
dotnet test (Join-Path 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT' 'RoNCT.sln')
```

Expected: build succeeds and all tests pass.

- [ ] **Step 2: Confirm working tree is clean**

```powershell
git -C 'C:\Users\curve\Documents\Codex\2026-09-07\RoNCT' status --short
```

Expected: no output (no uncommitted changes).
