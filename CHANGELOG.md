# Changelog

All notable changes are documented here.

## [1.0.0] - 2026-09-08

### Added

- C# / WinUI 3 rewrite with instant bilingual UI and system theme support
- One-click compatibility testing with safe per-group isolation
- In-process dependency analysis with conflict/group planning
- Cancellable test runs that keep the UI responsive
- Backup, rollback, quarantine with confirmation dialogs
- Nexus Mods identification, candidate chooser, requirement checks
- Startup calibration with cached results
- OCR-based main-menu detection with a stable fallback
- Debug diagnostics copied for bug reports
- Title-bar Help and About pages

### Changed

- Replaced the Python/Qt client with a self-contained C# application
- Analysis now runs in-process and no longer needs repak/UAssetCLI helpers
- Runtime data (logs, reports, backups) stays next to the executable

### Security

- `config.json`, logs, backups, quarantine, and reports are excluded from the
  repository
- Quarantine deletion requires explicit confirmation

### Fixed

- UI no longer freezes while calibration or tests are running
- Quarantine cannot be emptied by a single accidental click
- Settings persist correctly across restarts
