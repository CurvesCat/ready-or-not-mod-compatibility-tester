from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_rules(path: str | Path | None) -> dict[str, Any]:
    """Load user rules.json. Missing file -> empty rules; malformed file -> empty rules."""
    if path is None:
        return {}
    rules_path = Path(path)
    if not rules_path.is_file():
        return {}
    try:
        data = json.loads(rules_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data
