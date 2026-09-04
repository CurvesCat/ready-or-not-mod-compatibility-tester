from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import AppConfig, TestResult


CSV_COLUMNS = (
    "filename",
    "verdict",
    "elapsed_seconds",
    "reason",
    "log_excerpt",
    "started_at",
    "finished_at",
    "deployed_path",
    "quarantined_path",
    "mod_dir",
    "exe",
)


def write_reports(
    report_dir: Path,
    *,
    summary: dict[str, Any],
    results: list[TestResult],
    config: AppConfig,
) -> tuple[Path, Path]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_path = report_dir / f"mod_compat_report_{timestamp}.csv"
    json_path = report_dir / f"mod_compat_report_{timestamp}.json"
    ok_list_path = report_dir / "可用_mods.txt"
    bad_list_path = report_dir / "不可用_mods.txt"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for result in results:
            row = result.as_dict()
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})

    payload = {
        "summary": summary,
        "config": {
            "mod_folder": str(config.mod_folder) if config.mod_folder else "",
            "mod_files": [str(p) for p in config.mod_files],
            "exclude_files": [str(p) for p in config.exclude_files],
            "game_root": str(config.game_root) if config.game_root else "",
            "exe_path": str(config.exe_path) if config.exe_path else "",
            "mod_dir": str(config.mod_dir) if config.mod_dir else "",
            "mode": config.mode,
            "stable_seconds": config.stable_seconds,
            "startup_timeout": config.startup_timeout,
            "menu_hold_seconds": config.menu_hold_seconds,
            "close_timeout": config.close_timeout,
            "close_running": config.close_running,
            "backup_mods": config.backup_mods,
            "backup_dir": str(config.backup_dir) if config.backup_dir else "",
            "backup_max_file_mb": config.backup_max_file_mb,
            "backup_max_total_mb": config.backup_max_total_mb,
            "source": config.source,
            "disposition": config.disposition,
            "warmup": config.warmup,
            "extra_args": config.extra_args,
        },
        "results": [result.as_dict() for result in results],
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ok_names = [r.filename for r in results if r.verdict.value == "可用"]
    bad_names = [r.filename for r in results if r.verdict.value == "不可用"]
    ok_list_path.write_text(
        "\n".join(ok_names) + ("\n" if ok_names else ""),
        encoding="utf-8-sig",
    )
    bad_list_path.write_text(
        "\n".join(bad_names) + ("\n" if bad_names else ""),
        encoding="utf-8-sig",
    )
    return csv_path, json_path
