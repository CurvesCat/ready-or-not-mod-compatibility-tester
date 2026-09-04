# Ready or Not Mod Compatibility Tester

**Author:** CurvesCat

**Nexus Mods:** <https://www.nexusmods.com/readyornot/mods/8575>

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
  - **Candidate folder** — test a folder (or hand-picked files) of `.pak` mods.
  - **Installed in game folder** — test mods already placed in
    `ReadyOrNot\Content\Paks`.
- Exclude individual files, add single files, and clear the selection.
- Two strategies:
  - **Standard isolated** — test one mod at a time.
  - **Strict deep** — test one mod at a time with a longer observation window.
- Auto-detect the game root, executable, and Mod folder.
- **Auto timing** — launch the game once to measure startup time and suggest the
  stable-observation value.
- Auto-click to skip the intro animation.
- Detects crashes via process exit, error dialogs, and new `Saved\Crashes`
  directories.
- Backs up and verifies the Mod folder before testing; supports one-click
  **restore backup**.
- Handles unusable mods by moving to quarantine, renaming `.disabled`, deleting,
  or recording only.
- Reports in CSV / JSON plus `usable_mods.txt` / `unusable_mods.txt`.
- English and Chinese UI (language is asked on first launch and can be changed
  later).

## Requirements

- Windows 10 / 11
- Steam version of *Ready or Not* installed
- Steam logged in

Pre-built executables need no Python. To run from source, Python 3.10+ and
`psutil` are required.

## Quick start (GUI)

1. Run `ReadyOrNot-ModCompatTester.exe`.
2. Choose the language.
3. Pick the test source:
   - *Candidate folder*: choose a folder containing `.pak` files, or click
     *Add .pak files...*.
   - *Installed in game folder*: test the mods already installed.
4. Click *Auto detect* to locate the game.
5. Optional: click *Auto timing* to measure startup time.
6. Choose the strategy and how to handle unusable mods.
7. Click *Start test*.

Do not operate the game manually while the tool is running.

## Command line

```powershell
ReadyOrNot-ModCompatTester-cli.exe --mods "D:\Mods\RoN" --mode isolated
ReadyOrNot-ModCompatTester-cli.exe --source installed --mode isolated
```

Common options:

| Option | Description | Default |
| --- | --- | --- |
| `--mods` | Candidate folder | none |
| `--files` | Individual `.pak` files to test | none |
| `--exclude` | Files to exclude | none |
| `--source` | `folder` / `installed` | `folder` |
| `--mode` | `isolated` / `strict` | `isolated` |
| `--disposition` | `quarantine` / `disable` / `delete` / `record` | `quarantine` |
| `--yes-delete` | Confirm `--disposition delete` (required, otherwise rejected) | off |
| `--game` | Game root folder | auto-detect |
| `--exe` | Game executable | auto-detect |
| `--mod-dir` | Mod install folder | auto-detect |
| `--report-dir` | Report output folder | next to mod folder |
| `--stable` | Stable observation seconds | 35 |
| `--startup-timeout` | Window appearance timeout | 120 |
| `--warmup` | Launch once without mods first | off |
| `--extra-args` | Extra game launch args | `-windowed -nosplash` |
| `--backup-dir` | Backup folder | `backup` next to the exe |

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
according to your settings. Back up your saves and mods first. Use at your own
risk. The automated result is only a startup-stage smoke test.

---

## 中文说明

作者：CurvesCat

N 网页面：https://www.nexusmods.com/readyornot/mods/8575

这是一个 Windows 桌面工具，用于在《严阵以待》更新后自动逐个检测 `.pak` Mod
是否仍然可用。它会逐个把 Mod 放进游戏目录、启动游戏并观察窗口/进程是否稳定，
输出 CSV / JSON 报告，并可把不可用 Mod 隔离、禁用或删除。

注意：工具只能判断“启动/进主菜单阶段会不会崩”。如果 Mod 是进游戏后（选武器、进地图）
才失效，且启动阶段正常，工具无法自动发现，需要你手动进游戏验证。

功能包括：测试候选文件夹或游戏目录内已安装的 Mod、单独添加/排除文件、自动检测、
自动测时、点击跳过开场动画、备份与一键还原、中英文界面等。

请自行备份存档和 Mod，使用风险自负。
