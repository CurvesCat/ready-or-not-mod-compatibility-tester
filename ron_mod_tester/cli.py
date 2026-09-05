from __future__ import annotations

import argparse
import re
import sys
import threading
from pathlib import Path

from . import VERSION
from .models import AppConfig
from .runner import TestRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ron-mod-compat",
        description=(
            f"RoNCT (Ready or Not Mod Compatibility Tester) v{VERSION} - tests .pak "
            "mods one by one for startup compatibility."
        ),
    )
    parser.add_argument(
        "--mods",
        help="folder containing .pak mods (required when --source is folder)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=[],
        help="individual .pak files to test (multiple allowed)",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="files to exclude from testing",
    )
    parser.add_argument(
        "--game",
        help="game root folder (contains the ReadyOrNot folder)",
    )
    parser.add_argument("--exe", help="full path to the game executable")
    parser.add_argument(
        "--mod-dir",
        help="mod install folder (default: auto-detect Paks/~mods)",
    )
    parser.add_argument("--report-dir", help="report output folder")
    parser.add_argument(
        "--source",
        choices=("folder", "installed"),
        default="folder",
        help="test source: folder (candidate folder) or installed (default: folder)",
    )
    parser.add_argument(
        "--mode",
        choices=("isolated", "strict"),
        default="isolated",
        help="test strategy: isolated or strict (default: isolated)",
    )
    parser.add_argument(
        "--stable",
        type=int,
        default=35,
        help="stable observation seconds after the game window appears (default: 35)",
    )
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=120,
        help="timeout in seconds waiting for the game window (default: 120)",
    )
    parser.add_argument(
        "--menu-hold",
        type=int,
        default=6,
        help="extra observation seconds after the main-menu marker (default: 6)",
    )
    parser.add_argument(
        "--warmup",
        action="store_true",
        help="launch the game once without mods before the real test",
    )
    parser.add_argument(
        "--no-close",
        action="store_true",
        help="do not close an already running game before testing",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="write the state manifest only, do not copy backups",
    )
    parser.add_argument(
        "--backup-dir",
        help="backup folder (default: <report dir>/backup)",
    )
    parser.add_argument(
        "--backup-max-file-mb",
        type=int,
        default=1500,
        help="do not back up a single file above this size in MB (default: 1500)",
    )
    parser.add_argument(
        "--backup-max-total-mb",
        type=int,
        default=10000,
        help="maximum total backup size in MB (default: 10000)",
    )
    parser.add_argument(
        "--disposition",
        choices=("quarantine", "disable", "delete", "record"),
        default="quarantine",
        help=(
            "how to handle unusable mods: quarantine, disable, delete, or record "
            "(default: quarantine)"
        ),
    )
    parser.add_argument(
        "--yes-delete",
        action="store_true",
        help="confirm --disposition delete (required, otherwise rejected)",
    )
    parser.add_argument(
        "--extra-args",
        default="-windowed -nosplash",
        help='extra game launch arguments, e.g. "-windowed"',
    )
    parser.add_argument(
        "--static-scan",
        action="store_true",
        help="run static analysis (pak inventory + conflicts) without launching the game",
    )
    parser.add_argument(
        "--repak-exe",
        help="path to repak.exe used by --static-scan",
    )
    return parser


def _is_interactive() -> bool:
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except Exception:  # noqa: BLE001 - cosmetic only
        return False


def _wait_for_enter_if_interactive() -> None:
    if not _is_interactive():
        return
    try:
        print(flush=True)
        print("Press Enter to close this window.", flush=True)
        sys.stdin.readline()
    except Exception:  # noqa: BLE001 - cosmetic only
        pass


def _run_static_scan(args: argparse.Namespace) -> int:
    """T1 static scan: list every pak and report duplicate/overwrite conflicts."""
    from pathlib import Path

    from .static.analyzer import analyze_folder
    from .static.report import summarize, write_static_report

    mod_folder = Path(args.mods) if args.mods else None
    if mod_folder is None or not mod_folder.is_dir():
        print("Static scan requires --mods <folder containing .pak files>.", flush=True)
        return 2
    report_dir = (
        Path(args.report_dir)
        if args.report_dir
        else mod_folder.parent / (mod_folder.name + "_static_reports")
    )
    repak_exe = Path(args.repak_exe) if args.repak_exe else None

    analysis = analyze_folder(
        mod_folder,
        repak_exe=repak_exe,
        log=lambda text: print(text, flush=True),
    )
    json_path = write_static_report(report_dir, analysis)
    summary = summarize(analysis)

    print("\n=== Static scan finished ===", flush=True)
    print(
        f"paks {summary['paks']} / entries {summary['entries']} / "
        f"parse errors {summary['parse_errors']} / "
        f"duplicate groups {summary['duplicate_groups']} / "
        f"overwrite groups {summary['overwrite_groups']}",
        flush=True,
    )
    print(f"JSON report: {json_path}", flush=True)
    for conflict in analysis.conflicts[:20]:
        names = ", ".join(p.filename for p in conflict.providers)
        print(f"  [{conflict.kind}] {conflict.internal_path} -> {names}", flush=True)
    if len(analysis.conflicts) > 20:
        print(
            f"  ... and {len(analysis.conflicts) - 20} more conflict paths "
            f"(see JSON report)",
            flush=True,
        )
    return 0


_PATTERNS = [
    (r"^  已移入隔离区：(.+)$", r"  Moved to quarantine: \1"),
    (r"^  已禁用（重命名）：(.+)$", r"  Disabled (renamed): \1"),
    (r"^  已删除：(.+)$", r"  Deleted: \1"),
    (r"^  无法执行“(.+?)”：(.+)$", r"  Could not apply \"\1\": \2"),
    (r"^  无法恢复 (.+?)[：:](.+)$", r"  Could not restore \1: \2"),
    (r"^  未找到临时文件：(.+)$", r"  Temporary file not found: \1"),
    (r"^  已恢复：(.+)$", r"  Restored: \1"),
    (r"^  无法移出已安装 Mod：(.+)$", r"  Could not move installed mods: \1"),
    (r"无法移出已安装 Mod：(.+)", r"Could not move installed mods: \1"),
    (r"不安全的文件名：(.+)", r"Unsafe file name: \1"),
    (r"正在初始化…", r"Initializing..."),
    (r"请选择 Mod 文件夹，或手动添加至少一个 \.pak 文件。", r"Please choose a mod folder or add at least one .pak file."),
    (r"所选游戏根目录不存在：(.+)", r"Selected game root does not exist: \1"),
    (
        r"所选游戏根目录无效：未找到 ReadyOrNot\\Content\\Paks 或 ~mods 等已知 Mod 目录。",
        r"Selected game root is invalid: ReadyOrNot\\Content\\Paks or a known mod folder such as ~mods was not found.",
    ),
    (r"正在自动检测《严阵以待》安装目录…", r"Auto-detecting the Ready or Not installation folder..."),
    (
        r"未能自动检测到游戏目录。请手动选择游戏根目录（包含 ReadyOrNot 文件夹）。",
        r"Could not auto-detect the game folder. Please select the game root manually (it must contain the ReadyOrNot folder).",
    ),
    (r"找不到游戏可执行文件：(.+)", r"Game executable not found: \1"),
    (r"所选 Mod 安装目录不存在：(.+)", r"Selected mod install folder does not exist: \1"),
    (r"找不到游戏 Paks 目录：(.+)", r"Game Paks folder not found: \1"),
    (r"^游戏目录：(.+)$", r"Game folder: \1"),
    (r"^可执行文件：(.+)$", r"Executable: \1"),
    (r"^Mod 安装目录：(.+)$", r"Mod install folder: \1"),
    (r"^报告目录：(.+)$", r"Report folder: \1"),
    (r"^测试来源：游戏目录内已安装$", r"Test source: installed in game folder"),
    (r"^测试来源：候选文件夹$", r"Test source: candidate folder"),
    (r"^测试策略：标准隔离（逐个测试）$", r"Test strategy: standard isolated (one at a time)"),
    (r"^测试策略：严格深度（逐个，更长观察）$", r"Test strategy: strict deep (one at a time, longer observation)"),
    (
        r"警告：未检测到 Steam 正在运行，游戏可能无法通过 Steam 校验。",
        r"Warning: Steam does not appear to be running. The game may fail Steam validation.",
    ),
    (
        r"游戏进程已在运行。请先退出游戏，或勾选“测试前关闭已运行的游戏”。",
        r"The game is already running. Please close it first, or enable the option to close a running game before testing.",
    ),
    (r"检测到游戏正在运行，正在关闭…", r"A running game was detected; closing it..."),
    (r"已保存 Mod 目录状态清单：(.+)", r"Mod folder state manifest saved: \1"),
    (r"已创建备份目录：(.+)", r"Backup folder created: \1"),
    (
        r"游戏 Mod 目录中没有检测到已安装的非系统 \.pak Mod。",
        r"No installed non-system .pak mods were found in the game mod folder.",
    ),
    (r"检测到已安装 Mod (\d+) 个，正在移入临时区…", r"Detected \1 installed mod(s); moving them to the temporary area..."),
    (r"已移出，开始测试…", r"Moved out. Starting tests..."),
    (r"所选文件夹中没有检测到非系统 \.pak Mod 文件。", r"No non-system .pak mod files were found in the selected folder."),
    (r"待测试 Mod：(\d+) 个", r"Mods to test: \1"),
    (r"开始预热：不带 Mod 启动一次游戏…", r"Warmup: launching the game once without mods..."),
    (
        r"预热失败：干净状态下游戏无法正常启动。请检查游戏本体/Steam。",
        r"Warmup failed: the game could not start in a clean state. Check the game installation / Steam.",
    ),
    (r"预热完成。", r"Warmup complete."),
    (
        r"就地测试完成，已按处理方式恢复/隔离/禁用/删除对应 Mod。",
        r"Installed-mod test finished. Mods were restored, quarantined, disabled, or deleted according to the disposition.",
    ),
    (r"警告：Mod 目录状态与测试前不一致，请人工检查：", r"Warning: the mod folder state differs from before the test. Check it manually:"),
    (r"^  - 新增: ", r"  - Added: "),
    (r"^  - 缺失: ", r"  - Missing: "),
    (r"^  - 类型变化: ", r"  - Type changed: "),
    (r"^  - 大小变化: ", r"  - Size changed: "),
    (r"新增: ", r"Added: "),
    (r"缺失: ", r"Missing: "),
    (r"类型变化: ", r"Type changed: "),
    (r"大小变化: ", r"Size changed: "),
    (r"Mod 目录状态校验通过，未改动原有文件。", r"Mod folder state verification passed. Existing files were not changed."),
    (r"已请求停止，未完成的 Mod 标记为跳过。", r"Stop requested. Incomplete mods are marked as skipped."),
    (r"^\[(\d+)/(\d+)\] 正在测试：(.+)$", r"[\1/\2] Testing: \3"),
    (r"已取消，未完成测试", r"Canceled; test not completed"),
    (r"Mod 目录中已存在同名文件，已跳过（未覆盖）。", r"A file with the same name already exists in the mod folder; skipped without overwriting."),
    (r"Mod 目录中已存在同名文件：(.+)", r"A file with the same name already exists in the mod folder: \1"),
    (r"复制 Mod 到游戏目录失败：(.+)", r"Failed to copy the mod into the game folder: \1"),
    (r"无法启动游戏进程。", r"Could not start the game process."),
    (r"^  已启动游戏（PID (\d+)）…$", r"  Game started (PID \1)..."),
    (r"游戏主窗口已出现，开始观察…", r"The game main window appeared; starting observation..."),
    (r"开始持续点击跳过启动动画…", r"Continuously clicking to skip the intro animation..."),
    (r"观察中… 已等待 (\d+)s / (\d+)s", r"Observing... waited \1s / \2s"),
    (r"检测到错误弹窗：(.+)", r"Error dialog detected: \1"),
    (r"游戏日志出现致命/加载错误", r"Fatal or loading error found in the game log"),
    (r"检测到主菜单/引擎就绪标记，进入短确认窗口…", r"Main-menu / engine-ready marker detected; entering a short confirmation window..."),
    (r"生成崩溃报告：(.+)", r"Crash report generated: \1"),
    (r"启动超时（(\d+)s）或游戏进程未出现。", r"Startup timed out (\1s) or the game process never appeared."),
    (r"游戏启动后 ([\d.]+)s 异常退出，疑似崩溃。", r"The game exited unexpectedly \1s after starting; likely a crash."),
    (r"游戏进程存在，但 (\d+)s 内未出现主窗口（可能卡在加载）。", r"The process is alive, but no main window appeared within \1s (possibly stuck loading)."),
    (r"主菜单标记出现后保持稳定", r"Stable after the main-menu marker appeared"),
    (r"游戏主窗口保持稳定", r"Game main window remained stable"),
    (r"用户取消", r"Canceled by user"),
    (r"^  (.+) → 可用（批量通过）$", r"  \1 -> usable (passed in batch)"),
    (r"批量测试通过（检测到主菜单标记）", r"Batch test passed (main-menu marker detected)"),
    (r"批量测试通过", r"Batch test passed"),
    (r"合并启动测试剩余 (\d+) 个 Mod…", r"Batch launch: \1 mod(s) remaining..."),
    (r"合并测试剩余 (\d+) 个（第 (\d+) 轮启动）", r"Batch test: \1 remaining (launch round \2)"),
    (r"合并启动出错：(.+)，剩余 Mod 标记为错误。", r"Batch launch error: \1. Remaining mods marked as error."),
    (r"合并部署遇到同名冲突，改为逐个复核。", r"A name conflict occurred during batch deployment; switching to one-by-one verification."),
    (r"二分无法定位，可能存在 Mod 相互影响，改为逐个复核。", r"Binary search could not isolate the problem; mods may interact. Switching to one-by-one verification."),
    (r"定位到问题 Mod：(.+)（(.+)）", r"Problem mod located: \1 (\2)"),
    (r"未找到备份清单：(.+)", r"Backup manifest not found: \1"),
]


def _to_english(text: str) -> str:
    result = str(text)
    for pattern, replacement in _PATTERNS:
        result = re.sub(pattern, replacement, result)
    result = (
        result.replace("不可用", "unusable")
        .replace("可用", "usable")
        .replace("错误", "error")
        .replace("已存在", "conflict")
        .replace("跳过", "skipped")
        .replace("：", ": ")
        .replace("…", "...")
    )
    return result


def _show_launcher_hint() -> None:
    print("This is the command-line version; do not run it by double-clicking.", flush=True)
    print(flush=True)
    print("Run it from PowerShell or CMD, for example:", flush=True)
    print('  ReadyOrNot-ModCompatTester-cli.exe --mods "D:\\Mods\\RoN" --mode isolated', flush=True)
    print(flush=True)
    print("Without arguments there is nothing to run, so the program exits.", flush=True)


_VERDICT_LABELS = {
    "可用": "usable",
    "不可用": "unusable",
    "错误": "error",
    "已存在": "conflict",
    "跳过": "skipped",
}


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:  # noqa: BLE001 - cosmetic only
        pass

    argv_list = list(sys.argv[1:]) if argv is None else list(argv)
    if not argv_list:
        _show_launcher_hint()
        _wait_for_enter_if_interactive()
        return 2

    args = _build_parser().parse_args(argv_list)
    if args.static_scan:
        return _run_static_scan(args)
    if args.disposition == "delete" and not args.yes_delete:
        print(
            "Safety restriction: --disposition delete permanently deletes files. "
            "Add --yes-delete to confirm.",
            flush=True,
        )
        return 2
    print(
        "Warning: this tool launches the game and may modify the mod folder. "
        "Back up important saves and data first. Use at your own risk.",
        flush=True,
    )

    config = AppConfig(
        mod_folder=Path(args.mods) if args.mods else None,
        mod_files=[Path(p) for p in args.files],
        exclude_files=[Path(p) for p in args.exclude],
        game_root=Path(args.game) if args.game else None,
        exe_path=Path(args.exe) if args.exe else None,
        mod_dir=Path(args.mod_dir) if args.mod_dir else None,
        report_dir=Path(args.report_dir) if args.report_dir else None,
        source=args.source,
        mode=args.mode,
        stable_seconds=max(5, args.stable),
        startup_timeout=max(20, args.startup_timeout),
        menu_hold_seconds=max(1, args.menu_hold),
        close_running=not args.no_close,
        backup_mods=not args.no_backup,
        backup_dir=Path(args.backup_dir) if args.backup_dir else None,
        backup_max_file_mb=max(100, args.backup_max_file_mb),
        backup_max_total_mb=max(100, args.backup_max_total_mb),
        disposition=args.disposition,
        warmup=args.warmup,
        extra_args=args.extra_args,
    )

    cancel_event = threading.Event()

    def emit(kind: str, data: object) -> None:
        if kind == "log":
            print(_to_english(str(data)), flush=True)
        elif kind == "status":
            print(f"[status] {_to_english(str(data))}", flush=True)
        elif kind == "progress":
            done, total, name = data
            label = _to_english(str(name))
            print(f"[progress {done}/{total}] {label}", flush=True)
        elif kind == "result":
            verdict = _VERDICT_LABELS.get(data.verdict.value, data.verdict.value)
            print(f"  {verdict} - {data.filename}", flush=True)
        elif kind == "done":
            s = data
            print("\n=== Test finished ===", flush=True)
            print(
                f"usable {s['ok']} / unusable {s['fail']} / error {s['error']} / "
                f"conflict {s['conflict']} / skipped {s['skipped']} / total {s['total']}",
                flush=True,
            )
            print(f"CSV report: {s['csv_path']}", flush=True)
            print(f"JSON report: {s['json_path']}", flush=True)
            print(f"Backup folder: {s['backup_dir']}", flush=True)
            print(f"Quarantine folder: {s['quarantine_dir']}", flush=True)

    try:
        TestRunner(config=config, emit=emit, cancel_event=cancel_event).run()
        return 0
    except RuntimeError as exc:
        print(f"Error: {_to_english(str(exc))}", flush=True)
        return 1
    except KeyboardInterrupt:
        cancel_event.set()
        print("Stop requested.", flush=True)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
