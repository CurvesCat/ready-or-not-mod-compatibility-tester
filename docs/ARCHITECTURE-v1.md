# RoNCT (C#) v1 Architecture — Complete Rewrite That Outperforms Python

- Status: Accepted plan; implementation proceeds milestone by milestone.
- Date: 2026-09-07
- Goal: A Windows C#/WinUI 3 app that is a **superset** of the Python v0.4.2/0.5
  feature set, with two concrete wins over Python:
  1. Per-mod isolation tests that can attribute a crash to one mod.
  2. In-process asset analysis (no per-asset subprocess) so a full dependency
     scan is seconds, not ~1 minute.

## 1. Success criteria

- Feature parity with the Python release: selection, auto-detect, one-click
  test, dependency analysis, calibration, backup/restore, quarantine, Nexus
  identification + requirements, bilingual UI, reports.
- **Per-mod isolation**: each test group installs only that group's mods;
  everything else is parked and restored automatically and safely.
- **In-process analysis**: pak listing and UAsset import parsing run inside the
  process (no per-file `dotnet` spawn), reaching the 10-second-class scan the
  user's friend expects.
- Cancellation-safe, exit-safe, no stray game/helper processes, Mod directory
  verified after every mutation.
- Portable ZIP + per-user Setup EXE + GitHub auto-update.

## 2. Repository layout

```text
RoNCT.sln
├── src/RoNCT.Core        Pure domain: models, planning, analysis graphs,
│                         report writers, configuration, backup/verify logic.
├── src/RoNCT.Services    OS/tool adapters: game process engine, pak/asset
│                         parsers, deployment/isolation, quarantine/backup,
│                         Nexus HTTP, updater.
├── src/RoNCT.App         WinUI 3 shell + pages + view models.
├── tests/RoNCT.Tests     Unit tests for Core; parser fixtures; planner.
├── packaging/            Inno Setup script, publish profiles, updater manifest.
└── docs/
```

## 3. Core abstractions that make the speed win possible

```text
IPakInspector         ListPakAssets(pakPath) -> IReadOnlyList<string>
IPakFileReader        ReadFile(pakPath, internalPath) -> byte[]
IAssetParser          ParseImports(uasset, uexp?) -> AssetImports
IAssetAnalyzer        Uses IPakInspector + IAssetParser; produces edges
```

- Current adapters: `RepakProcess` implements `IPakInspector/IPakFileReader`
  via repak; `UAssetCliParser` implements `IAssetParser` via a dotnet
  subprocess. These exist for fallback and were already used to prove formats.
- Target adapters (default when available; license-safe by design):
  - `Cue4PakInspector` — CUE4Parse lists and reads pak files in-process.
  - `Cue4AssetParser` — CUE4Parse parses `.uasset` import tables in-process.
    UAssetAPI (GPL-3.0) is intentionally **not** linked in-process because it
    would conflict with the app's PolyForm Noncommercial license; the legacy
    UAssetCLI subprocess remains the only UAssetAPI-based path.
  - This removes one subprocess per asset; for ~100+ assets that is the whole
    1-minute → ~10-second gap.
- Selection between implementations is decided once by
  `AnalysisEngineFactory` (probe: can we load CUE4Parse/UAssetAPI? if yes use
  in-process; otherwise fall back to repak/UAssetCLI).

## 4. Isolation-aware test model (correctness)

Today's "one launch for all installed mods" cannot attribute a crash to one
mod. The architecture restores the Python model:

1. `ModFolderSnapshot` = which `.pak` files currently exist in the game Mod
   folder (names + sizes + hashes lazily).
2. For each test group:
   - **Park** every installed mod not in the group: move to an app-managed
     `quarantine/session-*` folder (never delete; recoverable).
   - **Deploy** candidate mods for the group into the Mod folder (copy or
     symlink; copy by default for safety).
   - Run `GameSession` (launch → observe → verdict).
   - **Restore**: remove deployed paks, move parked mods back.
   - Verify folder state against the pre-session snapshot; on any failure the
     next session is refused until state is consistent.
3. Grouping (`DeploymentPlanner`) reuses conflict pairs + dependency edges +
   user rules. With isolation, single-mod groups are correct and meaningful.

Interfaces:

```text
IModFolderOperator    Park(mods) / Deploy(mods) / Restore() / Verify()
IModFolderOperatorFactory -> RealModFolderOperator (BackupService-backed)
```

`RealModFolderOperator` is the only component allowed to mutate the game Mod
folder; everything else goes through it. Park/restore are log-based so a crash
mid-run can be recovered by re-running restore on next launch.

## 5. Dependency analysis result model

```text
PakInventory            pak + internal paths
AssetImports            import ObjectNames + soft package refs
DependencyEdge          fromMod -> toMod (+ confidence)
UnresolvedReference     /Game/Mods/... not provided by scanned mods
AnalysisReport          inventories, edges, unresolved, parse errors, stats
```

Unresolved refs are also compared against the base game (optional large scan)
so "missing prerequisite" reports do not list vanilla assets as missing.

## 6. Process/game safety

- `GameProcessService` matches the game by **process name** (already fixed for
  x86/x64), enumerates windows, clicks to skip intros.
- Every session ends with graceful close then `Kill(entireProcessTree)`.
- `GameSession` observes UE log markers, crash-reports dir, error dialogs,
  process exit, and window stability; always restores mod state.
- `AppLog` writes rotating `logs/debug.log`; every milestone logs phase starts
  and verdicts so field issues are debuggable.

## 7. UI

WinUI 3 + Fluent, Mica only when safe, system/light/dark, instant bilingual
switch. Pages: Test, Nexus, Backup, Quarantine, Advanced. Result cards + report
openers. Theme, localization, and layout already exist and are not the focus
of remaining work except regression checks.

## 8. Release & update

- Portable ZIP and Setup EXE built from the same publish output.
- The updater checks a configurable GitHub releases endpoint
  (`CurvesCat/ready-or-not-mod-compatibility-tester`), compares semantic
  versions, downloads the release asset, verifies a published SHA-256, stages,
  and applies on restart.
- Runtime packaging must be resolved for .NET 10 self-contained publish (the
  known WinRT load issue on this machine) before release; fallback is
  framework-dependent + a runtime installer step.

## 9. Milestone order (each ends green, committed, verified)

- **M0** — Current baseline is green: 29/29 tests; one-launch in-place test
  verified end-to-end (game launched, Ok, closed, reports written).
- **M1 — Isolation** (`IModFolderOperator` + session parking/restore +
  `GameSession` per group). Unlocks true per-mod verdicts.
- **M2 — In-process analysis** (CUE4Parse behind interfaces; benchmark vs
  subprocess path; target seconds).
- **M3 — Nexus/parity regression**, calibration wiring, remaining Python
  features that are still missing (compare against Python v0.4 UI list).
- **M4 — Release engineering**: self-contained publish fix, Inno Setup,
  updater, English docs, signing consideration.
- **M5 — Final integration test on a real machine + full parity audit**.

## 10. Risks / mitigations

- **WinUI/.NET self-contained publish issue** → isolate minimal repro; if SDK
  bug, pin runtime/SDK version or ship framework-dependent + bootstrapper.
- **Moving installed mods** is risky → park/restore only via
  `IModFolderOperator` with backups and startup recovery; tests run in a sandbox
  folder before first use on the real game folder.
- **CUE4Parse API drift** → keep repak/UAssetCLI fallback and fixture tests
  against real sample paks. Adding a GPL parser in-process is not an option
  under the PolyForm Noncommercial license.

## 11. Immediate next actions

1. Implement M1 isolation module with unit tests (sandbox folder).
2. Wire M1 into TestRunner (group per mod).
3. Run an end-to-end verification with 2-3 real mods (game launches a few
   times, ~3-5 minutes) and compare per-mod verdicts with manual reality.
