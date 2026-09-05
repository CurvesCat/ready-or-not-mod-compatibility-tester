from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import StaticAnalysis


def write_static_report(
    report_dir: Path, analysis: StaticAnalysis
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = report_dir / f"static_analysis_{timestamp}.json"
    json_path.write_text(
        json.dumps(analysis.as_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return json_path


def summarize(analysis: StaticAnalysis) -> dict[str, int]:
    return {
        "paks": len(analysis.paks),
        "entries": sum(p.entry_count for p in analysis.paks),
        "parse_errors": sum(0 if p.parse_ok else 1 for p in analysis.paks),
        "duplicate_groups": sum(1 for c in analysis.conflicts if c.kind == "duplicate"),
        "overwrite_groups": sum(1 for c in analysis.conflicts if c.kind == "overwrite"),
    }
