# RoNCT v1.0.0 — C# / WinUI 3 Rewrite Design

- **Date:** 2026-09-07
- **Status:** Approved for spec review (pending user review)
- **Author:** RoNCT maintainers (Codex-assisted)
- **Related:** Python/PySide6 v0.4.2 archived under `windows-ready-or-not-mod-mod`

## 1. Background and goals

RoNCT (Ready or Not Mod Compatibility Tester) currently ships as a Python /
PySide6 application (`ron_mod_tester`, v0.4.2). The GUI is a large monolithic
Qt file (~3,800 lines), background tasks are managed through worker threads,
and users have reported window flashing, stuck exits, and lingering hidden
processes.

This rewrite replaces the Python implementation with a modern C# / .NET /
WinUI 3 application. The user-facing name stays **RoNCT**. The first release
of the new codebase is **v1.0.0** and is treated as a brand-new product:
settings, caches, and reports from v0.4.x are **not** migrated.

Goals:

- Full functional parity with v0.4.2 (feature inventory in §4 is the acceptance
  baseline; no user-facing feature may regress).
- A layered architecture that separates UI, orchestration, and pure logic so
  that the core can be unit-tested and future bugs stay localized.
- Elimination of the historical symptoms: no console-window flashing, no
  zombie helper processes, cancellation-safe exit, and no data left outside
  the application directory.
- Windows 11 Fluent look and feel (Mica/Acrylic materials), bilingual UI
  (Simplified Chinese / English), light/dark/system theme.
- Distribution as both a portable ZIP and a per-user Setup EXE, plus a
  built-in self-update mechanism ready to be pointed at GitHub Releases later.

## 2. Non-goals (v1.0.0)

- No command-line version (retired with the Python line; legacy CLI stays in
  the archived Python repository only).
- No third-party mod-manager integration (e.g., RoN Mod Manager).
- No old-version data import or compatibility with v0.4.x file formats.
- No Microsoft Store / MSIX distribution and no paid code signing in v1.
- No automatic update hosting until the maintainer's GitHub account status is
  resolved; the feature is built but disabled/placeholder until then.
- No telemetry, analytics, or crash reporting uploads.

## 3. Confirmed decisions

| Topic | Decision |
| --- | --- |
| Language / UI stack | C#, .NET (LTS), WinUI 3 (Windows App SDK), unpackaged |
| Architecture strategy | Skeleton first, feature slices, full feature parity |
| Data compatibility | Brand new — no migration from Python v0.4.x |
| Product name | RoNCT (unchanged) |
| Versioning | Semantic versioning starting at 1.0.0 |
| Distribution | Portable ZIP + Setup EXE (Inno Setup), shared payload |
| Runtime packaging | Self-contained (users do not install .NET / Windows App SDK) |
| Auto-update | Built-in updater module; HTTPS JSON manifest; endpoint configurable |
| UI language | First launch English; one-click Chinese/English switch, remembered |
| Theme | System / Light / Dark; follows Windows when set to System |
| Backdrop materials | Mica on the main window; Acrylic on flyouts/menus/dialogs; Windows 10 falls back to solid surfaces |
| Data location | Everything generated lives inside the application directory unless the user explicitly chooses another target |
| License | PolyForm Noncommercial 1.0.0 (unchanged) |
| GitHub content | English only |

## 4. Feature inventory (parity baseline)

This is the acceptance checklist. Every slice of the implementation must map
back to one or more rows below.

### 4.1 Mod selection

- [ ] Folder selection (all `.pak` files inside) and single/multi `.pak` file
      selection through one unified picker flow.
- [ ] Auto-detect the Ready or Not installed Mod directory (game Paks folder).
- [ ] Manual browsing and remembering of game root / Mod folder / quarantine
      folder paths.
- [ ] Selected file list with per-item removal; selections persist between
      sessions; first launch starts with an empty list.

### 4.2 One-click test pipeline

- [ ] Auto-calibration of game startup timing (window wait, stable window,
      startup timeout); calibrated values persist.
- [ ] Safe deployment / in-place testing of installed mods; Mod-directory state
      snapshot, restore, and post-restore verification.
- [ ] Static duplicate / overwrite conflict scan.
- [ ] Asset dependency analysis (pak listing + asset reference parsing).
- [ ] Automatic grouping: interdependent mods share a launch group; conflicting
      mods are isolated.
- [ ] Per-group real game launch: wait for main window, auto-skip intros,
      observe stability for the configured window, detect crash/exit/error
      dialogs/new crash reports.
- [ ] Result statistics (usable / unusable / error / already present /
      skipped) and timestamped CSV + JSON reports.
- [ ] Cancel / stop / quick-exit during a run, with safe cleanup and no
      lingering hidden processes.

### 4.3 Standalone dependency analysis

- [ ] Analyze dependencies without launching the game.
- [ ] Preview dependency edges, unresolved references, and parse errors.
- [ ] Start the full test directly with the analyzed groups (no rescan).

### 4.4 Quarantine

- [ ] One-click move of unusable/error mods into the quarantine folder.
- [ ] Configurable quarantine directory (default: inside the app folder).
- [ ] Quarantine list view with delete action and an open-folder entry point.

### 4.5 Backup and restore

- [ ] Automatic Mod-directory backup before tests (configurable file/total
      size caps and manifest).
- [ ] One-click restore and an open-backup-folder entry point.

### 4.6 Nexus Mods integration

- [ ] API key entry/save, connection test, and guided "how to obtain the API
      key" tutorial.
- [ ] Identify the current folder: local MD5 fingerprint lookup on Nexus with
      fuzzy-name fallback.
- [ ] Confirm / ignore matches, remembered locally.
- [ ] Requirement check for confirmed mods with a missing-prerequisite summary.
- [ ] Local-but-unconfirmed mods reported as "present locally (confirm)" rather
      than falsely missing.
- [ ] Identification / requirement results persist to reports; rows link to
      the Nexus page.

### 4.7 UI and preferences

- [ ] Simplified-Chinese / English UI with instant switching (no restart).
- [ ] System / Light / Dark theme with instant switching.
- [ ] Advanced options: game executable path, launch arguments, calibration
      parameters, backup limits, quarantine path, excluded files, analysis
      tool paths.
- [ ] First-run tutorial, About dialog (version, contact, license, third-party
      notices), run-log viewer, open-report/open-quarantine/open-backup entries.

### 4.8 Privacy and operational baseline

- [ ] Generated files stay in `reports/`, `cache/`, `backup/`, `quarantine/`,
      `logs/` under the application directory by default.
- [ ] Rotating debug log (1 MB, keeps history).
- [ ] Helper processes run windowless (no console flash).

## 5. Architecture overview

### 5.1 Solution layout

```text
RoNCT.sln
├── src/
│   ├── RoNCT.Core/          Pure logic: models, planning, static analysis,
│   │                        dependency graph, report writers, config schema
│   ├── RoNCT.Services/      Runtime: game control, tool adapters, deployment,
│   │                        quarantine/backup, Nexus client, updater
│   └── RoNCT.App/           WinUI 3 UI: pages, view models, resources
├── tests/
│   └── RoNCT.Tests/         xUnit unit and integration tests
├── packaging/               Inno Setup scripts, ZIP layout, manifest template
├── docs/                    Design, build, and release documentation
└── assets/                  Logo, icons, about metadata
```

### 5.2 Project responsibilities and rules

**RoNCT.Core** (no UI, no OS-specific dependencies beyond .NET BCL)

- Configuration schema (`AppConfig`) and typed JSON persistence.
- Report schema and CSV/JSON writers.
- Static conflict scan (duplicate/overwrite detection).
- Dependency model and grouping/planner algorithm.
- Test result model, statistics, and summary rules.
- Error codes with localized display text.
- All of the above are unit-testable without files, processes, or a game.

**RoNCT.Services**

- `ITestRunner` orchestration: prepare → static scan → dependency analysis →
  plan → per-group execution → report.
- `IGameController`: launch, wait for `UnrealWindow`, auto-skip intros, detect
  crashes, close game.
- `IPakInspector` / `IAssetParser` adapters around repak / UAssetCLI
  subprocesses (windowless, cancellable). The interfaces allow future
  replacement with in-process .NET parsers without touching upper layers.
- `IDeployer`: safe Mod-folder deploy/restore with snapshot + verify.
- Quarantine and backup services (manifests, size caps).
- Nexus client (HTTPS, MD5 upload, requirement lookup, local cache).
- Update service (manifest fetch, download, SHA-256 verify, staged replace).
- Long-running and process-owning code lives only here.

**RoNCT.App**

- NavigationView shell and pages; view models translate UI actions to service
  calls; no business logic in code-behind.
- Localization resources (`zh-Hans`, `en`) and theme/material services.

**RoNCT.Tests**

- Core unit tests (algorithms, schemas, writers).
- Service integration tests against a fake game process and sandboxed
  directories.
- Manual E2E checklist for real-game release validation.

### 5.3 Key domain models

```text
ModItem            Selected pak + path, size, fingerprint, display name
TestRequest        Mod source, options, timing parameters, tool paths
StaticScanResult   Duplicates and overwrite conflicts
DependencyGraph    Edges, unresolved references, parse errors
Plan               Ordered TestGroup list with isolation metadata
TestGroup          Mods to launch together + expected behavior
TestItemResult     Per-group outcome + failure detail (error code, phase)
TestSummary        Usable/unusable/error/present/skipped counts, canceled flag
ReportBundle       Timestamped CSV + JSON artifacts
AppConfig          Settings persisted as JSON under the app directory
```

## 6. One-click pipeline (data flow)

1. UI builds a `TestRequest` from selections/settings and invokes
   `ITestRunner.RunAsync`.
2. Services perform preparation: verify game/tools, clear leftovers, snapshot
   the Mod directory, and (optionally) back it up.
3. Core runs the static conflict scan.
4. Services run dependency analysis (configurable) through tool adapters; Core
   parses results into a `DependencyGraph`.
5. Core plans ordered `TestGroup`s (dependencies together, conflicts isolated).
6. Services execute each group: deploy → launch → wait for window → skip intro
   → observe stable window → detect crash → close → restore Mod directory.
7. Core aggregates results and writes the CSV/JSON report; UI renders summary
   and per-group rows from the same result objects.
8. Canceled or partially failed runs still produce a report flagged with the
   cancellation/failure state.

## 7. Cancellation, stop, and safe exit

- One shared `CancellationToken` flows through every async operation.
- Stop cancels the current phase, closes the current game launch safely,
  restores the Mod directory, and reports partial results.
- Closing the window during work hides UI immediately, cancels the job, and
  runs the safe shutdown path: normal game close → helper grace period →
  force-stop only when stuck → directory restore → exit.
- A final safety fallback forces exit if cleanup is stuck and no game process
  remains (preserving v0.4.2 behavior).
- Every Mod-directory mutation is wrapped in snapshot/restore/finally with
  post-restore verification.

## 8. UI design

### 8.1 Navigation

```text
RoNCT main window (NavigationView)
├── Test           Select mods → one-click test / analyze only → progress →
│                  results summary and detail rows
├── Nexus          Identify folder, confirm/ignore, requirement checks, API key
├── Backup         Backup list, restore, open backup folder
├── Quarantine     Quarantine list, delete, open folder
└── Advanced       Paths, timing, limits, exclusions, tool settings
Bottom/corner: language switch · theme switch · check for updates · tutorial ·
About · open report folder · run log
```

### 8.2 Appearance and interaction

- Windows 11 Fluent: `NavigationView`, `ContentDialog`, system controls, rounded
  corners, default motion/animations.
- Main window uses Mica; flyouts/menus use Acrylic; Windows 10 degrades to solid
  surfaces automatically.
- Theme (System/Light/Dark) applies instantly by swapping the root theme and
  XAML resource dictionaries.
- Language switch applies instantly through a localization service that
  refreshes bound strings and view-model text without restart.
- Fonts: Windows default font stack only (Segoe UI Variable / 微软雅黑); no
  bundled fonts.
- Results render as per-item cards with clear usable/unusable/error colors.

## 9. Nexus integration behavior

- API key entered in-app and stored locally in the app directory; never logged
  and never committed.
- "Identify current folder" computes MD5 fingerprints and queries Nexus;
  fuzzy name matching is the fallback when fingerprint lookup fails.
- Confirm/ignore choices persist to the local Nexus cache; requirement checks
  compare confirmed mods against Nexus `requirements` and summarize missing
  prerequisites, treating identified-but-unconfirmed local mods as present.
- Online requests upload only fingerprints and the optional API key over HTTPS.

## 10. Packaging and distribution

### 10.1 Portable ZIP

```text
RoNCT-v1.0.0-win64/
├── RoNCT.exe
├── runtimes/ and app payload (self-contained)
├── assets/
├── README.md
├── CHANGELOG.md
├── LICENSE.txt
└── THIRD_PARTY_NOTICES.txt
```

Runtime data directories are created next to the executable on first launch.

### 10.2 Setup EXE

- Built with Inno Setup from the same payload.
- Per-user install under `%LocalAppData%\Programs\RoNCT` (no administrator
  rights required).
- Start-menu/desktop shortcuts and an uninstaller.
- Data-directory policy is identical to the portable build.

## 11. Auto-update

- `UpdateService` checks a configurable HTTPS manifest URL (JSON) containing
  version, asset URLs (ZIP/setup), SHA-256 hashes, and release notes.
- On update: download to an `updates/` staging folder inside the app directory,
  verify hashes, apply on next launch, and roll back automatically on failure.
- The endpoint is empty/placeholder until GitHub hosting is available; the UI
  reports "check for updates unavailable" rather than an error.

## 12. Testing strategy

- xUnit unit tests for Core: grouping/planner, conflict scanner, report
  writers, config round-trip, dependency parsing fixtures.
- Service integration tests: pipeline against a fake game controller and
  sandboxed directories to exercise cancellation and restore paths without a
  real game.
- Release validation: documented manual E2E checklist runs the real Ready or
  Not game and ticks every row of the feature inventory.

## 13. Security and privacy

- HTTPS only for Nexus and update traffic.
- No telemetry, analytics, or log uploads.
- Runtime data directories are gitignored; config/secret files can never be
  committed from the repository.
- Generated data remains inside the application directory unless the user
  explicitly targets another folder.
- Update downloads are verified against published SHA-256 hashes.

## 14. Versioning, documentation, and licensing

- Semantic versioning from 1.0.0; English CHANGELOG.
- GitHub-facing content (README, docs, releases) is English.
- License: PolyForm Noncommercial 1.0.0.
- Third-party components (.NET, Windows App SDK, repak, UAssetCLI/UAssetAPI,
  Inno Setup, test libraries) tracked in `THIRD_PARTY_NOTICES.txt`.

## 15. Risks and open items

- GitHub account is under review; repository hosting and update URLs are
  deferred until resolved.
- Mica/Acrylic require Windows 11; Windows 10 must render solid fallbacks
  without visual breakage.
- repak/UAssetCLI remain subprocess adapters initially; in-process .NET
  parsing is a possible later swap behind the same interfaces.
- Real-game validation remains a manual step (cannot run headless in CI).
- Nexus API availability and rate limits depend on the user's API key and
  subscription tier.

## 16. Acceptance mapping

Each implementation milestone must:

1. Reference the relevant §4 checklist identifiers.
2. Pass Core/Service automated tests where applicable.
3. Pass the manual E2E checklist for any game-launch behavior.
4. Update the README/CHANGELOG/THIRD_PARTY_NOTICES as needed.

