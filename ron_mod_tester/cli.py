from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

from . import APP_NAME, VERSION
from .models import AppConfig
from .runner import TestRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ron-mod-compat",
        description=(
            f"{APP_NAME} v{VERSION}：逐个测试《严阵以待》的 .pak Mod 兼容性。"
        ),
    )
    parser.add_argument("--mods", help="包含 .pak Mod 文件的文件夹路径（source=folder 时必填）")
    parser.add_argument(
        "--files",
        nargs="*",
        default=[],
        help="单独指定要测试的 .pak 文件（可多个）",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="排除这些文件，不参与测试",
    )
    parser.add_argument("--game", help="游戏根目录（包含 ReadyOrNot 文件夹）")
    parser.add_argument("--exe", help="游戏可执行文件完整路径")
    parser.add_argument("--mod-dir", help="Mod 安装目录（默认自动检测 Paks/~mods）")
    parser.add_argument("--report-dir", help="报告输出目录")
    parser.add_argument(
        "--source",
        choices=("folder", "installed"),
        default="folder",
        help="测试来源：folder=候选文件夹，installed=游戏目录内已安装（默认 folder）",
    )
    parser.add_argument(
        "--mode",
        choices=("isolated", "strict"),
        default="isolated",
        help="测试策略：isolated=标准隔离(逐个)，strict=严格深度(逐个更长观察)（默认 isolated）",
    )
    parser.add_argument(
        "--stable",
        type=int,
        default=35,
        help="游戏主窗口出现后的稳定观察秒数（默认 35）",
    )
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=120,
        help="等待游戏进程出现的超时秒数（默认 120）",
    )
    parser.add_argument(
        "--menu-hold",
        type=int,
        default=6,
        help="检测到主菜单标记后再观察的秒数（默认 6）",
    )
    parser.add_argument(
        "--warmup",
        action="store_true",
        help="正式测试前先不带 Mod 启动一次游戏预热/验证基线",
    )
    parser.add_argument(
        "--no-close",
        action="store_true",
        help="测试前不自动关闭已运行的游戏（若已在运行则中止）",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="不复制备份，仅生成目录状态清单",
    )
    parser.add_argument("--backup-dir", help="备份目录（默认 <报告目录>/backup）")
    parser.add_argument(
        "--backup-max-file-mb",
        type=int,
        default=1500,
        help="单个文件超过该大小(MB)则不复制备份（默认 1500）",
    )
    parser.add_argument(
        "--backup-max-total-mb",
        type=int,
        default=10000,
        help="备份总大小上限(MB)（默认 10000）",
    )
    parser.add_argument(
        "--disposition",
        choices=("quarantine", "disable", "delete", "record"),
        default="quarantine",
        help="不可用 Mod 处理方式：quarantine=移入隔离区，disable=重命名禁用，"
        "delete=删除，record=仅记录（默认 quarantine）",
    )
    parser.add_argument(
        "--extra-args",
        default="-windowed -nosplash",
        help='附加游戏启动参数（例如 "-windowed"）',
    )
    return parser


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

    args = _build_parser().parse_args(argv)
    print(
        "警告：本工具会启动游戏并可能改动 Mod 目录。请先备份重要存档与数据，使用风险自负。",
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
            print(str(data), flush=True)
        elif kind == "status":
            print(f"[状态] {data}", flush=True)
        elif kind == "progress":
            done, total, name = data
            print(f"[进度 {done}/{total}] {name}", flush=True)
        elif kind == "result":
            print(f"  结果：{data.verdict.value} - {data.filename}", flush=True)
        elif kind == "done":
            s = data
            print("\n=== 测试完成 ===", flush=True)
            print(
                f"可用 {s['ok']} / 不可用 {s['fail']} / 错误 {s['error']} / "
                f"已存在 {s['conflict']} / 跳过 {s['skipped']} / 共 {s['total']}",
                flush=True,
            )
            print(f"CSV 报告：{s['csv_path']}", flush=True)
            print(f"JSON 报告：{s['json_path']}", flush=True)
            print(f"备份目录：{s['backup_dir']}", flush=True)
            print(f"隔离目录：{s['quarantine_dir']}", flush=True)

    try:
        TestRunner(config=config, emit=emit, cancel_event=cancel_event).run()
        return 0
    except RuntimeError as exc:
        print(f"错误：{exc}", flush=True)
        return 1
    except KeyboardInterrupt:
        cancel_event.set()
        print("已请求停止。", flush=True)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
