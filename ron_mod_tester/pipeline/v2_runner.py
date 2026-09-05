from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .. import SHORT_NAME, VERSION


def build_v2_report(
    static_report: dict[str, Any],
    dep_report: dict[str, Any] | None,
    plan_report: dict[str, Any],
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Combine T1/T2/T3 outputs into the V2 report structure."""
    mods = list(plan_report.get("mods") or [])
    conflicts = list(static_report.get("conflicts") or [])
    conflict_mods: set[str] = set()
    for conflict in conflicts:
        if conflict.get("kind") == "overwrite":
            for provider in conflict.get("providers") or []:
                name = str(provider.get("filename"))
                if name:
                    conflict_mods.add(name)

    needs_manual = sorted(conflict_mods)
    dynamic_status = "dry_run" if dry_run else "pending"
    return {
        "schema": "ronct.v2.report",
        "app": {"name": SHORT_NAME, "version": VERSION},
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "mod_folder": str(static_report.get("mod_folder", "")),
            "mod_count": len(mods),
            "mods": mods,
        },
        "static_analysis": {
            "pak_count": len(static_report.get("paks") or []),
            "conflicts": conflicts,
            "dependency_edges": (
                list((dep_report or {}).get("edges") or [])
            ),
            "per_mod_status": {
                mod: ("suspicious" if mod in conflict_mods else "needs_dynamic")
                for mod in mods
            },
            "warnings": list(static_report.get("warnings") or []),
        },
        "plan": {
            "deploy_groups": list(plan_report.get("deploy_groups") or []),
            "conflict_pairs": list(plan_report.get("conflict_pairs") or []),
        },
        "dynamic_results": {
            "status": dynamic_status,
            "per_test": [],
        },
        "final_verdict": {
            "usable": [],
            "unusable": [],
            "needs_manual_check": needs_manual,
            "confidence": {},
            "note": (
                "dry-run: 已生成测试计划，尚未启动游戏执行。"
                if dry_run
                else "计划已生成，等待动态执行。"
            ),
        },
    }


def write_v2_report(report_dir: Path, report: dict[str, Any]) -> Path:
    import json

    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = report_dir / f"v2_report_{timestamp}.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
