# Ready or Not Mod Compatibility Tester (RoNCT)

<p align="center"><img src="assets/logo.png" alt="RoNCT" width="120"></p>

**Author:** CurvesCat

**Short name:** RoNCT

**Nexus Mods:** <https://www.nexusmods.com/readyornot/mods/8575>

## Download

**One file, everything inside (GUI + tools + docs):**
Latest release: <https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester/releases>

A Windows desktop tool that checks whether each `.pak` mod still works after a
*Ready or Not* game update. It scans mods statically, analyzes cross-mod
dependencies, then starts the game in dependency-aware groups, watches the
window and process, and produces CSV / JSON reports while quarantining broken
mods.

> This tool only detects **startup / main-menu stage crashes**. If a mod breaks
> later (for example, when equipping a weapon or loading a mission), it cannot
> be detected automatically because *Ready or Not* does not write a standard
> Unreal Engine log.

## GUI (v0.3)

- **Windows 11 Fluent-style interface** built with PySide6/Qt. It no longer uses
  the old tkinter interface.
- The UI theme **follows the Windows light/dark setting automatically**.
- Simplified **one-click workflow**: choose a Mod folder → click the primary
  button → read the result. No technical knowledge required.
- The **advanced options** are collapsed by default (strategy, timings, launch
  arguments, handling of unusable mods, game root).
- Nexus Mods API key can be saved locally for optional dependency lookups.
- Chinese / English UI switchable at any time from the left navigation.

## Features

- Two test sources:
  - **Candidate folder** - test a folder of `.pak` mods.
  - **Installed in game folder** - when the selected folder is the game `Paks`
    directory, RoNCT automatically tests the installed mods in place and
    restores them afterwards.
- Auto-detect the game root, executable, and Mod install folder.
- **Smart one-click pipeline**:
  - Static scan for duplicate / overwrite conflicts.
  - Dependency analysis of cooked Unreal assets.
  - Automatic planning: interdependent mods launch together, conflicting mods
    stay isolated.
  - Real game launches with auto-skip of the intro and crash detection.
- Detects crashes via process exit, error dialogs, crash dumps under
  `Saved\Crashes`, and available game logs.
- Records the Mod directory state before testing and creates an automatic
  backup; **restore backup** is available from the left navigation.
- Ignores game system files such as `pakchunk*-Windows.pak`.
- Handles unusable mods by moving them to quarantine, renaming them
  `.disabled`, or recording only (delete is intentionally not exposed in the
  simplified GUI).
- Reports in CSV / JSON plus usable/unusable text lists.

## Requirements

- Windows 10 / 11
- Steam version of *Ready or Not* installed
- Steam logged in

Pre-built executables do not need Python. To run from source, Python 3.10+ with
`psutil` and `PySide6` are required.

## Quick start (GUI)

1. Run `ReadyOrNot-ModCompatTester.exe`.
2. Click **Browse…** and choose a folder containing `.pak` files (or select the
   game `Paks` folder to test the mods already installed there).
3. Click **One-click test** and wait. The game will open several times - do not
   operate it manually while testing.
4. Read the result card and open the report folder when finished.

Default report folders:

- Candidate-folder source: `*_test_reports` next to the candidate folder.
- Installed source: `RoN_ModCompat_Reports` next to the game directory.

## Run from source

```powershell
python -m pip install -r requirements.txt
python -m ron_mod_tester
```

The legacy CLI entry point (`run_cli.py`, `ron_mod_tester/cli.py`) is kept only
as historical code and is no longer maintained or shipped in releases.

## Build the executable

See [BUILD.md](BUILD.md).

## Disclaimer

This tool launches the game repeatedly and may move, rename, or delete mod files
according to your settings. Back up your saves and mods first. Use it at your
own risk. The automated result is only a startup-stage smoke test.
