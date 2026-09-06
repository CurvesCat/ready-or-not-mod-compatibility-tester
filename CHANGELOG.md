# Changelog

All notable changes to RoNCT are documented here.

## [0.4.1] - 2026-09-06

### Added

- CONTRIBUTING, SECURITY, and CODE_OF_CONDUCT guides.
- GitHub issue templates, pull-request template, Dependabot, and CI workflow.
- EditorConfig and Git attributes for consistent formatting.
- Moved the legacy CLI usage document under `docs/`.
- `ronct.dev@icloud.com` contact shown in the About dialog and docs.

### Fixed

- Dependency / asset scans now respond to cancellation, so pressing Stop or
  closing the window no longer waits indefinitely on stuck analysis helpers.
- Closing during a running task hides the window immediately, cancels the job,
  and safely force-stops stuck repak/UAssetCLI helper processes after a grace
  period. Game shutdown and Mod-folder cleanup still follow the normal safe path.

## [0.4.0] - 2026-09-06

### Added

- Standalone **Analyze asset dependencies only** workflow with a results dialog
  covering dependency edges, unresolved references, parse errors, and a test
  group preview.
- **Start test with these groups** action so a completed dependency analysis can
  directly launch the real test without rescanning.
- One-click pipeline can reuse precomputed static/dependency/plan results.
- Clear progress reporting during asset dependency analysis.
- "Analyze asset dependencies before tests" advanced toggle (default enabled)
  for one-click runs.
- Missing-prerequisite summary in the Nexus dependency dialog.
- Local mods that are identified but not yet confirmed are treated as
  "Present locally (confirm)" instead of falsely reported as missing.
- Open backup folder entry in the navigation.
- Backup restore dialog now shows backup time, file count, recorded target
  directory, and disabled-backup warnings.
- Run log dialog falls back to `debug.log` history when no in-session log lines
  exist.

### Changed

- Mod folder / `.pak` selections and advanced settings persist immediately and
  on exit; first launch still starts empty.
- Manually selected `.pak` files are scanned and tested only, instead of
  scanning their whole parent directory.
- Theme switch label shortened to Light / Dark / Auto.
- Dark-mode navigation hover color fixed (was rendering as opaque yellow).
- Duplicate report/quarantine buttons removed from the one-click result card.
- repak and UAssetCLI subprocesses run without flashing console windows.
- README, tutorial, and packaging documentation updated to release quality.

### Removed

- MiSans font assets and related license files from the repository; the UI now
  uses the Windows system font stack.

## [0.3.0] - Earlier

- Windows 11 Fluent-style GUI rewrite.
- Theme switching, language switching, auto-calibration, and one-click
  dependency-aware testing.
