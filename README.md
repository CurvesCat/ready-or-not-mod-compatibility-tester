# Ready or Not Mod Compatibility Tester (RoNCT)

**Author:** CurvesCat

**Short name:** RoNCT

**Nexus Mods:** <https://www.nexusmods.com/readyornot/mods/8575>

## Download

**One file, everything inside (GUI + CLI + docs + license):**
[Download ReadyOrNot-ModCompatTester_v0.1.5.zip](https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester/releases/download/v0.1.5/ReadyOrNot-ModCompatTester_v0.1.5.zip)

Other releases: <https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester/releases>

A Windows desktop tool that automatically tests whether each `.pak` mod still
works after a *Ready or Not* game update. It launches the game once per mod,
watches the game window and process, and produces CSV / JSON reports while
quarantining or removing broken mods.

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

## Requirements

- Windows 10 / 11
- Steam version of *Ready or Not* installed
- Steam logged in

Pre-built executables do not need Python. To run from source, Python 3.10+ and
`psutil` are required.

## Quick start (GUI)

1. Run `ReadyOrNot-ModCompatTester.exe`.
2. Choose the interface language.
3. Pick the test source:
   - *Candidate folder*: choose a folder containing `.pak` files, or click
     *Add .pak files...*.
   - *Installed in game folder*: test the mods already installed.
4. Click *Auto detect* to locate the game.
5. Optional: click *Auto timing* to measure startup time.
6. Choose the strategy, the stable-observation seconds, and how to handle
   unusable mods.
7. Click *Start test*.

Do not operate the game manually while the tool is running.

## Command line

```powershell
ReadyOrNot-ModCompatTester-cli.exe --mods "D:\Mods\RoN" --mode isolated
ReadyOrNot-ModCompatTester-cli.exe --source installed --mode strict
```

Detailed command-line usage: [CLI_USAGE.txt](CLI_USAGE.txt)

Common options:

| Option | Description | Default |
| --- | --- | --- |
| `--mods` | Candidate folder of `.pak` mods | none |
| `--files` | Individual `.pak` files to test | none |
| `--exclude` | Files to exclude from testing | none |
| `--source` | `folder` / `installed` | `folder` |
| `--mode` | `isolated` / `strict` | `isolated` |
| `--disposition` | `quarantine` / `disable` / `delete` / `record` | `quarantine` |
| `--yes-delete` | Confirm `--disposition delete` (required, otherwise rejected) | off |
| `--game` | Game root folder | auto-detect |
| `--exe` | Game executable | auto-detect |
| `--mod-dir` | Mod install folder | auto-detect |
| `--report-dir` | Report output folder | next to the mod folder |
| `--stable` | Stable observation seconds after the game window appears | 35 |
| `--startup-timeout` | Timeout for the game window to appear | 120 |
| `--menu-hold` | Extra observation seconds after the main-menu marker | 6 |
| `--warmup` | Launch once without mods before the real test | off |
| `--no-close` | Do not close an already running game before testing | off |
| `--no-backup` | Record state only, do not copy backups | off |
| `--backup-dir` | Backup folder | `backup` next to the exe |
| `--backup-max-file-mb` | Do not copy a single file above this size (MB) | 1500 |
| `--backup-max-total-mb` | Backup total size limit (MB) | 10000 |
| `--extra-args` | Extra game launch arguments | `-windowed -nosplash` |

Default report folders:

- `folder` source: `*_test_reports` next to the candidate folder.
- `installed` source: `RoN_ModCompat_Reports` next to the game directory.

## Run from source

```powershell
python -m pip install psutil
python -m ron_mod_tester                       # GUI
python -m ron_mod_tester --mods "D:\Mods\RoN" --mode isolated   # CLI
```

## Build the executable

See [BUILD.md](BUILD.md).

## Disclaimer

This tool launches the game repeatedly and may move, rename, or delete mod files
according to your settings. Back up your saves and mods first. Use it at your
own risk. The automated result is only a startup-stage smoke test.
