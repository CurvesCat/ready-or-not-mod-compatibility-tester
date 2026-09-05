"""Compare confirmed local mods against Nexus requirements (read-only)."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .. import app_root
from .client import NexusClient
from .mapping import load_user_mapping

SCHEMA = 2


def default_requirements_cache_path() -> Path:
    return app_root() / "cache" / "nexus_requirements_cache.json"


def _load_req_cache(path: Path | None = None) -> dict[str, dict[str, Any]]:
    cache_path = path or default_requirements_cache_path()
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict) or int(data.get("schema") or 0) != SCHEMA:
        return {}
    entries = data.get("entries") if isinstance(data, dict) else {}
    if not isinstance(entries, dict):
        return {}
    return {str(key): value for key, value in entries.items() if isinstance(value, dict)}


def _save_req_cache(
    entries: dict[str, dict[str, Any]], path: Path | None = None
) -> None:
    cache_path = path or default_requirements_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({"schema": SCHEMA, "entries": entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(cache_path)
    except OSError:
        pass


def build_dependency_report(
    api_key: str,
    emit: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
    req_cache_path: Path | None = None,
    mapping_path: Path | None = None,
    local_mods: list[dict] | None = None,
) -> dict[str, Any]:
    """Check every user-confirmed mod for missing Nexus requirements."""
    client = NexusClient(api_key)
    mapping = load_user_mapping(mapping_path)
    confirmed: list[dict[str, Any]] = []
    owned_ids: set[int] = set()
    for md5, record in mapping.items():
        if not isinstance(record, dict) or record.get("choice") != "confirmed":
            continue
        try:
            mod_id = int(record.get("mod_id") or 0)
        except (TypeError, ValueError):
            continue
        if mod_id <= 0:
            continue
        confirmed.append(
            {
                "md5": md5,
                "pak_name": record.get("pak_name") or "",
                "mod_id": mod_id,
                "mod_name": record.get("mod_name") or "",
                "mod_url": record.get("mod_url") or "",
            }
        )
        owned_ids.add(mod_id)

    # A mod present in the latest identification pass is treated as available
    # even before the user confirms it, so we do not report false "missing".
    local_ids: set[int] = set(owned_ids)
    local_names: dict[int, str] = {}
    for item in local_mods or []:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        if status not in ("found", "cached", "candidate"):
            continue
        try:
            mod_id = int(item.get("mod_id") or 0)
        except (TypeError, ValueError):
            continue
        if mod_id <= 0:
            continue
        local_ids.add(mod_id)
        local_names.setdefault(
            mod_id,
            str(item.get("pak_name") or Path(str(item.get("pak") or "")).name or ""),
        )

    cache = _load_req_cache(req_cache_path)
    rows: list[dict[str, Any]] = []
    total = len(confirmed)
    for index, item in enumerate(confirmed, start=1):
        if cancel_event is not None and cancel_event.is_set():
            break
        if emit:
            emit(index, max(total, 1), item.get("pak_name") or item.get("mod_name") or "")
        mod_id = int(item["mod_id"])
        cached = cache.get(str(mod_id))
        if not cached or not isinstance(cached, dict) or "nexus" not in cached:
            try:
                req = client.mod_requirements(mod_id)
            except Exception as exc:  # noqa: BLE001 - one mod must not stop the rest
                rows.append(
                    {
                        **item,
                        "kind": "error",
                        "req_id": None,
                        "req_name": "",
                        "status": "error",
                        "notes": str(exc),
                        "url": "",
                    }
                )
                continue
            cached = {
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "dlc": req.get("dlc") or [],
                "nexus": req.get("nexus") or [],
            }
            cache[str(mod_id)] = cached

        for dlc in cached.get("dlc") or []:
            rows.append(
                {
                    **item,
                    "kind": "dlc",
                    "req_id": None,
                    "req_name": (dlc or {}).get("name") or "",
                    "status": "dlc",
                    "notes": (dlc or {}).get("notes") or "",
                    "url": "",
                }
            )
        for req in cached.get("nexus") or []:
            try:
                req_id = int(req.get("mod_id") or 0)
            except (TypeError, ValueError):
                req_id = 0
            external = bool(req.get("external"))
            if external:
                status = "external"
            elif req_id in owned_ids:
                status = "installed"
            elif req_id in local_ids:
                status = "local_candidate"
            else:
                status = "missing"
            rows.append(
                {
                    **item,
                    "kind": "external" if external else "mod",
                    "req_id": req_id if not external else None,
                    "req_name": req.get("mod_name") or "",
                    "status": status,
                    "notes": req.get("notes") or "",
                    "url": req.get("url") or "",
                    "local_pak": local_names.get(req_id, "") if not external else "",
                }
            )

    _save_req_cache(cache, req_cache_path)
    return {
        "confirmed_count": len(confirmed),
        "checked_count": len(set(int(r["mod_id"]) for r in rows if r.get("mod_id"))),
        "rows": rows,
    }
