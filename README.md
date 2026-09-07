# RoNCT - Ready or Not Mod Compatibility Tester

<p align="center">
  <strong>Automatically test <em>Ready or Not</em> `.pak` mods after game updates.</strong><br>
  Dependency-aware game launches · asset-level conflict analysis · CSV/JSON reports
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078D6?logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white" alt="PySide6">
  <img src="https://img.shields.io/github/v/release/CurvesCat/ready-or-not-mod-compatibility-tester" alt="Latest release">
  <img src="https://img.shields.io/github/last-commit/CurvesCat/ready-or-not-mod-compatibility-tester" alt="Last commit">
</p>

---

## Table of contents

- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Nexus Mods integration](#nexus-mods-integration)
- [Data, backups, and privacy](#data-backups-and-privacy)
- [Limitations](#limitations)
- [Development](#development)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

## About

RoNCT checks whether each `.pak` mod still works after a *Ready or Not* game
update. It statically scans mods for conflicts, analyzes asset-level
dependencies, then launches the game in dependency-aware groups, watches the
window and process, and produces CSV / JSON reports.

The GUI is a Windows 11 Fluent-style interface with a light/dark/auto theme,
English and Chinese UI, and no technical setup required for normal use.

Maintainer contact: [ronct.dev@icloud.com](mailto:ronct.dev@icloud.com)

## Features

- **Windows 11 Fluent-style GUI** built with PySide6/Qt.
- Theme follows Windows automatically; a Light / Dark / Auto switch is available
  in the status bar.
- Chinese and English UI, switchable with one click from the left navigation.
- Two test sources:
  - A **candidate folder** of `.pak` mods.
  - The game's **Paks folder**, where installed mods are tested in place and
    restored afterwards.
- Native folder or multi-file `.pak` pickers; manually selected files are the
  only files scanned and tested.
- **One-click pipeline**:
  1. Static scan for duplicate / overwrite conflicts.
  2. Asset dependency analysis (which mod references which).
  3. Automatic grouping: interdependent mods launch together, conflicting mods
     stay isolated.
  4. Real game launches with crash detection.
  5. CSV / JSON report generation.
- **Standalone dependency analysis** that previews test groups, then lets you
  start the real test with the exact same grouping without rescanning.
- Auto-calibrates game startup timing before tests.
- Optional **Nexus Mods API** integration:
  - identify local `.pak` files,
  - confirm/ignore matches (remembered locally),
  - check Nexus "Requirements" and summarize missing prerequisites.
- Automatic Mod-directory backup and one-click restore.
- Optional **GitHub-based auto-update**: "Check for updates" queries GitHub
  Releases for the newest version and opens the release page to download it.
- All generated data stays inside the software folder by default:
  `reports/`, `quarantine/`, `backup/`, `cache/`, and `debug.log`.

## Installation

### Release ZIP (recommended)

Download the latest release:

<https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester/releases/latest>

The release ZIP is self-contained:

```text
RoNCT-v0.4.2-win64/
├── ReadyOrNot-ModCompatTester.exe
├── _internal/            # bundled Python/Qt runtime (keep next to the exe)
├── tools/                # repak, UAssetCLI, portable .NET runtime
├── assets/               # application logo
├── README.md
├── CHANGELOG.md
├── LICENSE.txt
└── THIRD_PARTY_NOTICES.txt
```

No Python, .NET, or additional runtime installation is required.

### Run from source

```powershell
python -m pip install -r requirements.txt
python run_gui.py
```

Requirements: Windows 10 / 11, Python 3.10+, and the Steam version of
*Ready or Not* with Steam logged in.

## Quick start

1. Extract the release ZIP and run `ReadyOrNot-ModCompatTester.exe`.
2. Click **Select mods ▾** and choose a folder, or pick `.pak` files directly.
   Use **Auto detect** to load the game's installed mods.
3. Click **One-click test**. The game opens several times; do not operate it
   manually during the run.
4. Read the results, then use **Open report folder** in the left navigation.

Prefer a quick look at dependencies first?

1. Select the mods as above.
2. Click **Analyze asset dependencies only**.
3. Review dependency / unresolved-reference / group-preview tabs.
4. Click **Start test with these groups** to run the full test immediately.

## How it works

1. A candidate `.pak` is deployed into the game Mod folder (or installed mods
   are tested in place).
2. The game is launched and the main window (`UnrealWindow`) is awaited.
3. RoNCT auto-clicks to skip the intro until the observation ends.
4. Crash / exit / error dialog / new crash report during the window marks the
   group as unusable.
5. Staying stable for the configured time marks the group as usable.
6. The game is closed after each group and moved files are restored/removed.

See [BUILD.md](BUILD.md) for executable packaging and
[docs/legacy-cli.md](docs/legacy-cli.md) for the retired CLI.

## Nexus Mods integration

The Nexus feature is optional and read-only.

- **Identify current mod folder** fingerprints each `.pak` (MD5) and looks it
  up on Nexus, with fuzzy name matching as a fallback.
- Confirmed/ignored mappings are stored locally in `cache/nexus_known_mods.json`.
- **Check confirmed dependencies** reads Nexus "Requirements", compares them
  with your confirmed mods, and summarizes missing prerequisites.
- Local mods that are identified but not yet confirmed are shown as
  "Present locally (confirm)" instead of being falsely reported as missing.

Online requests upload only the file fingerprint (MD5) and your Personal API
key to `nexusmods.com`; file contents are never uploaded.

## Data, backups, and privacy

- The API key is stored in `config.json` next to the executable and is never
  committed to the repository.
- Reports, caches, backups, quarantine, and logs are created next to the
  executable unless you choose another location in Advanced options.
- The debug log rotates at 1 MB and keeps three history files.

## Limitations

- RoNCT reliably detects **startup / main-menu stage crashes**.
- It cannot detect problems that appear later in-game (e.g. equipping an item
  or loading a mission) because *Ready or Not* does not write a standard
  Unreal Engine log.
- Repeated game launches read large game files; test in batches.

## Development

See [BUILD.md](BUILD.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

Security reports should be sent privately - see [SECURITY.md](SECURITY.md).

## Contributing

Bug reports, feature requests, and pull requests are welcome. Please read
[CONTRIBUTING.md](CONTRIBUTING.md) first.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

PolyForm Noncommercial 1.0.0 - see [LICENSE](LICENSE).

Third-party components and their licenses are listed in
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

## Disclaimer

This tool launches the game repeatedly and may move, rename, or delete mod
files according to your settings. Back up your saves and mods first and use it
at your own risk.
