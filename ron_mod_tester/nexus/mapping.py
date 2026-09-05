"""User confirmations for pak fingerprints (kept inside the software folder)."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import app_root

SCHEMA = 1


def default_user_mapping_path() -> Path:
    return app_root() / "cache" / "nexus_known_mods.json"


def load_user_mapping(path: Path | None = None) -> dict[str, dict[str, Any]]:
    cache_path = path or default_user_mapping_path()
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in entries.items():
        if isinstance(key, str) and isinstance(value, dict):
            out[key.strip().lower()] = value
    return out


def save_user_mapping(
    entries: dict[str, dict[str, Any]], path: Path | None = None
) -> bool:
    cache_path = path or default_user_mapping_path()
    data = {"schema": SCHEMA, "entries": entries}
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(cache_path)
        return True
    except OSError:
        return False


def confirm_mod(
    entries: dict[str, dict[str, Any]],
    md5: str,
    mod_id: int | None,
    mod_name: str,
    mod_url: str,
    pak_name: str = "",
    author: str = "",
) -> None:
    key = (md5 or "").strip().lower()
    if not key:
        return
    entries[key] = {
        "choice": "confirmed",
        "mod_id": mod_id,
        "mod_name": mod_name or "",
        "mod_url": mod_url or "",
        "pak_name": pak_name or "",
        "author": author or "",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def ignore_mod(entries: dict[str, dict[str, Any]], md5: str) -> None:
    key = (md5 or "").strip().lower()
    if not key:
        return
    entries[key] = {
        "choice": "ignored",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


_LOCK = threading.Lock()


def confirm_md5(
    md5: str,
    mod_id: int | None,
    mod_name: str,
    mod_url: str,
    pak_name: str = "",
    author: str = "",
    path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    with _LOCK:
        entries = load_user_mapping(path)
        confirm_mod(entries, md5, mod_id, mod_name, mod_url, pak_name, author)
        save_user_mapping(entries, path)
        return entries


def ignore_md5(md5: str, path: Path | None = None) -> dict[str, dict[str, Any]]:
    with _LOCK:
        entries = load_user_mapping(path)
        ignore_mod(entries, md5)
        save_user_mapping(entries, path)
        return entries
