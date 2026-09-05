# RoNCT - Ready or Not Mod Compatibility Tester

<p align="center">
  <img src="assets/logo.png" alt="RoNCT" width="128">
</p>

**Author:** [CurvesCat](https://github.com/CurvesCat)

**Short name:** RoNCT

**Nexus Mods:** <https://www.nexusmods.com/readyornot/mods/8575>

RoNCT checks whether each `.pak` mod still works after a *Ready or Not* game
update. It scans mods statically, analyzes cross-mod asset dependencies, then
launches the game in dependency-aware groups, watches the window and process,
and produces CSV / JSON reports. Unusable mods can be quarantined, disabled,
recorded, or (with an explicit confirmation) deleted.

> **Scope:** RoNCT reliably detects startup / main-menu crashes. It cannot see
> problems that appear only later in-game (e.g. equipping an item or loading a
> mission) because *Ready or Not* does not write a standard Unreal Engine log.

---

## Download

Latest release (single ZIP with the GUI, bundled tools, licenses, and docs):

<https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester/releases/latest>

## Features

- **Windows 11 Fluent-style GUI** built with PySide6/Qt.
- Theme follows Windows automatically; a Light / Dark / Auto switch is available
  in the status bar.
- Chinese and English UI, switchable with one click from the left navigation.
- Two test sources:
  - A **candidate folder** of `.pak` mods.
  - The game's **Paks folder**, where installed mods are tested in place and
    restored afterwards.
- Native folder or multi-file `.pak` pickers. Only the files you selected are
  scanned when you choose `.pak` files manually.
- **One-click pipeline**:
  1. Static scan for duplicate / overwrite conflicts.
  2. Asset dependency analysis (which mod references which).
  3. Automatic grouping: interdependent mods launch together, conflicting mods
     stay isolated.
  4. Real game launches with crash detection.
  5. CSV / JSON report generation.
- **Standalone dependency analysis** that previews test groups, then lets you
  start the real test with the exact same grouping without re-scanning.
- Auto-calibrates game startup timing before tests.
- Optional **Nexus Mods API** integration:
  - identify local `.pak` files,
  - confirm/ignore matches (remembered locally),
  - check Nexus "Requirements" and summarize missing prerequisites.
- Records the Mod directory state before testing and creates an automatic
  backup; restore is available from the left navigation.
- All generated data stays inside the software folder by default:
  `reports/`, `quarantine/`, `backup/`, `cache/`, and `debug.log`.
- Ignores game system files such as `pakchunk*-Windows.pak`.

## Requirements

- Windows 10 / 11
- Steam version of *Ready or Not*, Steam logged in
- For source builds: Python 3.10+ (`psutil`, `PySide6`)

The release ZIP needs no Python or .NET installation: it bundles repak,
UAssetCLI, and a portable .NET runtime under `tools/`.

## Quick start (GUI)

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

## Data & privacy

- The Nexus feature is optional and read-only. When used, RoNCT sends only the
  local file fingerprint (MD5) and your Personal API key to
  `nexusmods.com`; it never uploads file contents.
- The API key is stored in `config.json` next to the executable and is never
  committed to the repository.
- Reports, caches, backups, quarantine, and logs are created next to the
  executable unless you choose another location in Advanced options.

## Run from source

```powershell
python -m pip install -r requirements.txt
python run_gui.py
```

The legacy CLI (`run_cli.py`, `ron_mod_tester/cli.py`) is retained only as
historical code and is not maintained or shipped.

## Build the executable

See [BUILD.md](BUILD.md) and the scripts under `packaging/`.

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
