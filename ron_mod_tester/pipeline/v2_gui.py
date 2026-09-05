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
) -> dict[str, Any]:
    """Run the full V2 pipeline from a GUI-style AppConfig."""
    repak_exe = str(tools.get("repak_exe") or "")
    dotnet_exe = str(tools.get("dotnet_exe") or "")
    uasset_cli = str(tools.get("uasset_cli_dll") or "")
    if not repak_exe or not dotnet_exe or not uasset_cli:
        raise RuntimeError(
            "V2 需要先在配置中登记 repak_exe、dotnet_exe、uasset_cli_dll。"
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
        raise RuntimeError("V2 测试需要一个有效的 Mod 文件夹。")

    emit("status", "V2 静态扫描：读取 pak 清单与冲突…")
    static = analyze_folder(folder, repak_exe=repak_exe, log=log)
    emit("status", "V2 依赖解析：分析资产引用（可能需要几分钟）…")
    dependency = scan_dependencies(
        folder,
        repak_exe=repak_exe,
        dotnet_exe=dotnet_exe,
        uasset_cli_dll=uasset_cli,
        engine=str(tools.get("engine") or "VER_UE5_4"),
        asset_limit=int(tools.get("asset_limit") or 0),
        workers=int(tools.get("workers") or 4),
        log=log,
    )

    rules_path = Path(str(tools.get("rules") or ""))
    rules = (
        load_rules(rules_path)
        if rules_path.name
        else {
            "mods": {},
        }
    )
    plan = build_plan(
        static.as_dict(),
        dependency,
        rules=rules,
        log=log,
    )

    emit("status", f"V2 计划完成：{len(plan.groups)} 组，开始动态测试…")
    runner = TestRunner(config=config, emit=emit, cancel_event=cancel_event)
    summary = runner.run(plan_groups=plan.as_dict()["deploy_groups"])

    if config.report_dir:
        report_dir = Path(config.report_dir)
    else:
        report_dir = folder.parent / (folder.name + "_v2_reports")
    v2_report = build_v2_report(
        static.as_dict(),
        dependency,
        plan.as_dict(),
        dry_run=False,
        dynamic_summary=summary,
    )
    v2_path = write_v2_report(report_dir, v2_report)
    summary["v2_report"] = str(v2_path)
    return summary
