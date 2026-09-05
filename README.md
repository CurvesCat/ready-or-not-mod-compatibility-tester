# Ready or Not Mod Compatibility Tester (RoNCT)

**Author:** CurvesCat

**Short name:** RoNCT

**Nexus Mods:** <https://www.nexusmods.com/readyornot/mods/8575>

## Download

**One file, everything inside (GUI + docs + license):**
[Download ReadyOrNot-ModCompatTester_v0.2.1.zip](https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester/releases/download/v0.2.1/ReadyOrNot-ModCompatTester_v0.2.1.zip)

Other releases: <https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester/releases>

A Windows desktop tool that checks whether each `.pak` mod still works after a
*Ready or Not* game update. It first scans the mods without launching the game,
then starts the game in dependency-aware groups, watches the window and
process, and produces CSV / JSON reports while quarantining or removing broken
mods.

> This tool only detects **startup / main-menu stage crashes**. If a mod breaks
> later (for example, when equipping a weapon or loading a mission), it cannot
> be detected automatically because *Ready or Not* does not write a standard
> Unreal Engine log.

## Features

- Two test sources:
  - **Candidate folder** - test a folder (or hand-picked files) of `.pak` mods.
  - **Installed in game folder** - test mods already placed in the game `Paks`.
- Add individual `.pak` files, exclude selected files, or clear the selection.
- Two strategies:
  - **Standard isolated** - test one mod at a time.
  - **Strict deep** - test one mod at a time with a longer observation window.
- Auto-detect the game root, executable, and mod install folder.
- **Auto timing** - launch the game once to measure startup time and suggest the
  stable-observation value.
- Auto-click to skip the intro animation while the game window opens.
- Detects crashes via process exit, error dialogs, crash dumps under
  `Saved\Crashes`, and available game logs.
- Records the mod folder state before testing, creates an optional backup, and
  supports one-click **restore backup**.
- Ignores game system files such as `pakchunk*-Windows.pak`.
- Handles unusable mods by moving them to quarantine, renaming them `.disabled`,
  deleting them, or recording only.
- Reports in CSV / JSON plus `usable_mods.txt` / `unusable_mods.txt`.
- English and Chinese UI. The language is selected on first launch and can be
  changed later.
- Configurable backup folder and backup size limits.

## Smart testing

- **Static scan** reads every `.pak` and reports duplicate/overwrite conflicts
  without launching the game.
- **Dependency analysis** parses cooked Unreal assets to find cross-mod
  references (for example "BluePrints requires Assets").
- **Automatic deploy planning** groups interdependent mods into one launch and
  keeps conflicting mods isolated.
- The full pipeline runs from the **One-click test** button in the GUI.

## Requirements

- Windows 10 / 11
- Steam version of *Ready or Not* installed
- Steam logged in

Pre-built executables do not need Python. To run from source, Python 3.10+ and
`psutil` are required.

## Quick start (GUI)

1. Run `ReadyOrNot-ModCompatTester.exe`.
2. Choose the interface language.
3. Click *Browse* and choose a folder containing `.pak` files.
4. Click **One-click test**.

Do not operate the game manually while the tool is running.

Default report folders:

- `folder` source: `*_test_reports` next to the candidate folder.
- `installed` source: `RoN_ModCompat_Reports` next to the game directory.

## Run from source

```powershell
python -m pip install psutil
python -m ron_mod_tester
```

## Build the executable

See [BUILD.md](BUILD.md).

## Disclaimer

This tool launches the game repeatedly and may move, rename, or delete mod files
according to your settings. Back up your saves and mods first. Use it at your
own risk. The automated result is only a startup-stage smoke test.
