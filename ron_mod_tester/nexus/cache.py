"""Small on-disk cache for Nexus MD5 lookups (kept in the software folder)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .. import app_root
from .client import GAME_DOMAIN

SCHEMA = 2
_FOUND_MAX_AGE_DAYS = 180
_UNKNOWN_MAX_AGE_DAYS = 7


def default_nexus_cache_path() -> Path:
    return app_root() / "cache" / "nexus_md5_cache.json"


class Md5Cache:
    """JSON cache mapping pak MD5 -> last Nexus lookup result."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_nexus_cache_path()
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        self._load()

    def get(self, md5: str) -> dict[str, Any] | None:
        key = (md5 or "").strip().lower()
        if not key:
            return None
        with self._lock:
            entry = self._entries.get(key)
            if not entry:
                return None
            queried_at = entry.get("queried_at")
            if queried_at:
                try:
                    age = datetime.now() - datetime.fromisoformat(str(queried_at))
                except ValueError:
                    age = timedelta(days=3650)
                max_age = (
                    timedelta(days=_FOUND_MAX_AGE_DAYS)
                    if entry.get("found")
                    else timedelta(days=_UNKNOWN_MAX_AGE_DAYS)
                )
                if age > max_age:
                    self._entries.pop(key, None)
                    return None
            return dict(entry)

    def put(self, md5: str, entry: dict[str, Any]) -> None:
        key = (md5 or "").strip().lower()
        if not key:
            return
        with self._lock:
            self._entries[key] = dict(entry)

    def save(self) -> bool:
        data = {
            "schema": SCHEMA,
            "game": GAME_DOMAIN,
            "entries": self._entries,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp.replace(self.path)
            return True
        except OSError:
            return False

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict) or int(data.get("schema") or 0) != SCHEMA:
            return
        entries = data.get("entries") if isinstance(data, dict) else None
        if isinstance(entries, dict):
            for key, value in entries.items():
                if isinstance(key, str) and isinstance(value, dict):
                    self._entries[key.strip().lower()] = value
