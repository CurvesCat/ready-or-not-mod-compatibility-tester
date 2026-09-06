from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from ..models import AppConfig
from ..planner.planner import build_plan
from ..planner.rules import load_rules
from ..runner import TestRunner
from ..static.analyzer import analyze_folder
from ..static.deps import scan_dependencies
from .v2_runner import build_v2_report, write_v2_report


EmitFn = Callable[[str, Any], None]


def run_v2_gui(
    config: AppConfig,
    tools: dict[str, Any],
    emit: EmitFn,
    cancel_event: Any,
    pre_static: dict[str, Any] | None = None,
    pre_dependency: dict[str, Any] | None = None,
    pre_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full V2 pipeline; optionally skip rescanning with precomputed results."""
    repak_exe = str(tools.get("repak_exe") or "")
    dotnet_exe = str(tools.get("dotnet_exe") or "")
    uasset_cli = str(tools.get("uasset_cli_dll") or "")
    if not repak_exe or not dotnet_exe or not uasset_cli:
        raise RuntimeError(
            "一键测试需要可用的工具组件（repak / UAssetCLI / .NET）。"
        )

    def log(text: str) -> None:
        emit("log", text)

    folder: Path | None = None
    if config.source == "folder":
        folder = config.mod_folder
        if folder is None and config.mod_files:
            folder = config.mod_files[0].parent
    elif config.mod_dir:
        folder = config.mod_dir
    if folder is None or not folder.is_dir():
        raise RuntimeError("一键测试需要一个有效的 Mod 文件夹。")
    manual_paks: list[Path] | None = None
    if config.source == "folder" and config.mod_folder is None:
        manual_paks = [
            path for path in config.mod_files if path.is_file()
        ] or None

    if pre_static is not None:
        static_report = pre_static
        dependency = pre_dependency if isinstance(pre_dependency, dict) else {}
        emit("status", "已沿用刚才的资产依赖分析结果，准备开始游戏测试…")
    else:
        emit("status", "正在体检 Mod：读取文件清单与冲突…")
        static = analyze_folder(
            folder,
            repak_exe=repak_exe,
            log=log,
            only_paks=manual_paks,
            cancel_event=cancel_event,
        )
        static_report = static.as_dict()
        dependency = None
        if bool(tools.get("analyze_deps", True)):
            emit("status", "正在分析 Mod 间资产依赖（逐个解析资产，可能需要几分钟）…")

            def dep_progress(done: int, total: int, name: str) -> None:
                emit("progress", (int(done), int(total), str(name)))

            dependency = scan_dependencies(
                folder,
                repak_exe=repak_exe,
                dotnet_exe=dotnet_exe,
                uasset_cli_dll=uasset_cli,
                engine=str(tools.get("engine") or "VER_UE5_4"),
                asset_limit=int(tools.get("asset_limit") or 0),
                workers=int(tools.get("workers") or 4),
                log=log,
                progress=dep_progress,
                only_paks=manual_paks,
                cancel_event=cancel_event,
            )
        else:
            emit("status", "已跳过资产级依赖分析（可在高级选项中重新开启）…")

    if pre_plan is None:
        rules_path = Path(str(tools.get("rules") or ""))
        rules = (
            load_rules(rules_path)
            if rules_path.name
            else {
                "mods": {},
            }
        )
        plan = build_plan(
            static_report,
            dependency,
            rules=rules,
            log=log,
        )
        plan_dict = plan.as_dict()
    else:
        plan_dict = pre_plan

    emit(
        "status",
        f"测试计划完成：{len(plan_dict.get('deploy_groups') or [])} 组，开始游戏测试…",
    )
    runner = TestRunner(config=config, emit=emit, cancel_event=cancel_event)
    summary = runner.run(plan_groups=plan_dict["deploy_groups"])

    if config.report_dir:
        report_dir = Path(config.report_dir)
    else:
        report_dir = folder.parent / (folder.name + "_v2_reports")
    v2_report = build_v2_report(
        static_report,
        dependency,
        plan_dict,
        dry_run=False,
        dynamic_summary=summary,
    )
    v2_path = write_v2_report(report_dir, v2_report)
    summary["v2_report"] = str(v2_path)
    return summary
