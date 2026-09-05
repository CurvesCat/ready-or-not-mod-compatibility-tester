"""Fingerprint local pak files and look them up on Nexus by MD5."""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .cache import Md5Cache
from .client import GAME_DOMAIN, NexusAuthError, NexusClient

STATUS_FOUND = "found"
STATUS_CACHED = "cached"
STATUS_CANDIDATE = "candidate"
STATUS_UNKNOWN = "unknown"
STATUS_ERROR = "error"

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_COMMON_TOKENS = {
    "addon",
    "addons",
    "and",
    "asset",
    "assets",
    "blueprint",
    "blueprints",
    "bp",
    "content",
    "contents",
    "dlc",
    "fix",
    "fixed",
    "fixes",
    "main",
    "mod",
    "mods",
    "new",
    "no",
    "pack",
    "packs",
    "pak",
    "pakchunk",
    "plus",
    "texture",
    "textures",
    "the",
    "ui",
    "uis",
    "update",
    "updated",
}

_TERM_VARIANTS = {
    "fastrelod": ["fast", "reload"],
    "relod": ["reload"],
    "relods": ["reload"],
    "shutgun": ["shotgun"],
    "shutguns": ["shotguns"],
    "shotgunreload": ["shotgun", "reload"],
}


@dataclass
class Identification:
    pak: Path
    md5: str = ""
    status: str = STATUS_UNKNOWN
    mod_id: int | None = None
    mod_name: str = ""
    file_name: str = ""
    version: str = ""
    mod_url: str = ""
    detail: str = ""
    matches: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)

    @property
    def pak_name(self) -> str:
        return self.pak.name

    def as_dict(self) -> dict[str, Any]:
        return {
            "pak": str(self.pak),
            "pak_name": self.pak_name,
            "md5": self.md5,
            "status": self.status,
            "mod_id": self.mod_id,
            "mod_name": self.mod_name,
            "file_name": self.file_name,
            "version": self.version,
            "mod_url": self.mod_url,
            "detail": self.detail,
            "candidates": self.candidates,
        }


def compute_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def identify_paks(
    paks: list[Path],
    api_key: str,
    cache: Md5Cache | None = None,
    emit: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
    min_interval: float = 1.1,
) -> list[Identification]:
    """Identify every pak. Unknown results are cached briefly; found ones long-term."""
    client = NexusClient(api_key, min_interval=min_interval)
    md5_cache = cache or Md5Cache()
    results: list[Identification] = []
    fail_streak = 0

    for index, pak in enumerate(paks, start=1):
        if cancel_event is not None and cancel_event.is_set():
            break
        if emit:
            emit(index, len(paks), pak.name)
        try:
            md5 = compute_md5(pak)
            cached = md5_cache.get(md5)
            if cached is not None:
                if cached.get("found"):
                    results.append(_from_cache(pak, md5, cached))
                else:
                    results.append(_from_unknown_cache(pak, md5, cached))
                fail_streak = 0
                continue

            matches = _normalize_matches(client.search_md5(md5))
            if matches:
                best = matches[0]
                record = {
                    "found": True,
                    "mod_id": best.get("mod_id"),
                    "mod_name": best.get("mod_name") or "",
                    "file_name": best.get("file_name") or "",
                    "version": best.get("version") or "",
                    "mod_url": best.get("mod_url") or "",
                    "queried_at": datetime.now().isoformat(timespec="seconds"),
                }
                md5_cache.put(md5, record)
                results.append(
                    Identification(
                        pak=pak,
                        md5=md5,
                        status=STATUS_FOUND,
                        mod_id=record["mod_id"],
                        mod_name=record["mod_name"],
                        file_name=record["file_name"],
                        version=record["version"],
                        mod_url=record["mod_url"],
                        matches=matches,
                    )
                )
            else:
                item, record = _search_candidates(client, pak, md5)
                md5_cache.put(md5, record)
                results.append(item)
            fail_streak = 0
        except NexusAuthError:
            raise
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the rest
            fail_streak += 1
            results.append(
                Identification(pak=pak, status=STATUS_ERROR, detail=str(exc))
            )
            if fail_streak >= 3:
                break

    md5_cache.save()
    return results


def _from_cache(pak: Path, md5: str, entry: dict[str, Any]) -> Identification:
    return Identification(
        pak=pak,
        md5=md5,
        status=STATUS_CACHED,
        mod_id=entry.get("mod_id"),
        mod_name=entry.get("mod_name") or "",
        file_name=entry.get("file_name") or "",
        version=entry.get("version") or "",
        mod_url=entry.get("mod_url") or "",
    )


def _from_unknown_cache(
    pak: Path, md5: str, entry: dict[str, Any]
) -> Identification:
    candidates = entry.get("candidates") or []
    if isinstance(candidates, list) and candidates:
        return _candidate_result(pak, md5, [c for c in candidates if isinstance(c, dict)])
    return Identification(pak=pak, md5=md5, status=STATUS_UNKNOWN)


def _search_candidates(
    client: NexusClient,
    pak: Path,
    md5: str,
) -> tuple[Identification, dict[str, Any]]:
    """Fuzzy-match file-name keywords against Nexus mod names."""
    now = datetime.now().isoformat(timespec="seconds")
    raw_terms = _query_terms(pak.name)
    terms: list[str] = []
    for raw in raw_terms[:3]:
        for variant in _TERM_VARIANTS.get(raw, [raw]):
            if variant not in terms:
                terms.append(variant)
        if len(terms) >= 4:
            break

    combined: dict[int, dict[str, Any]] = {}
    order = 0
    for term in terms[:4]:
        for match in client.search_mods(term, limit=8):
            mod_id = match.get("mod_id")
            if mod_id is None:
                continue
            entry = combined.get(mod_id)
            if entry is None:
                entry = dict(match)
                entry["_order"] = order
                entry["_matched"] = 1
                combined[mod_id] = entry
                order += 1
            else:
                entry["_matched"] = int(entry.get("_matched") or 0) + 1

    def score(entry: dict[str, Any]) -> tuple[int, int, int]:
        name_hits = _name_token_hits(
            str(entry.get("mod_name") or ""), raw_terms
        )
        total = int(entry.get("_matched") or 0) * 4 + name_hits
        return (-total, int(entry.get("_order") or 0), -name_hits)

    ranked = sorted(combined.values(), key=score)
    candidates = []
    for entry in ranked[:10]:
        candidates.append(
            {
                "mod_id": entry.get("mod_id"),
                "mod_name": entry.get("mod_name") or "",
                "author": entry.get("author") or "",
                "mod_url": entry.get("mod_url") or "",
                "matched_terms": entry.get("_matched"),
            }
        )
    if candidates:
        record: dict[str, Any] = {
            "found": False,
            "queried_at": now,
            "candidates": candidates,
        }
        return _candidate_result(pak, md5, candidates), record
    record = {"found": False, "queried_at": now}
    return Identification(pak=pak, md5=md5, status=STATUS_UNKNOWN), record


def _name_token_hits(mod_name: str, raw_terms: list[str]) -> int:
    """Count how many distinct pak-name tokens appear in the Nexus mod name."""
    if not raw_terms:
        return 0
    lower = re.sub(r"[^a-z0-9]+", " ", mod_name.lower())
    words = set(lower.split())
    hits = 0
    for term in raw_terms:
        if term in words:
            hits += 1
    return hits


def _candidate_result(
    pak: Path, md5: str, candidates: list[dict[str, Any]]
) -> Identification:
    best = candidates[0]
    return Identification(
        pak=pak,
        md5=md5,
        status=STATUS_CANDIDATE,
        mod_id=best.get("mod_id"),
        mod_name=best.get("mod_name") or "",
        version="",
        file_name=best.get("author") or "",
        mod_url=best.get("mod_url") or "",
        candidates=candidates,
    )


def _query_terms(pak_name: str) -> list[str]:
    """Turn a pak file name into short English search keywords."""
    stem = Path(pak_name).stem
    stem = re.sub(r"^pakchunk\d+[-_]*", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"(?i)[-_]*p$", "", stem)
    stem = _CAMEL_RE.sub(" ", stem)
    raw_tokens = re.split(r"[\s_.\-+()\[\]{}]+", stem)
    terms: list[str] = []
    for token in raw_tokens:
        low = token.strip().strip("_").lower()
        if (
            not low
            or low in _COMMON_TOKENS
            or low.isdigit()
            or len(low) < 3
        ):
            continue
        if low not in terms:
            terms.append(low)
    return terms


def _normalize_matches(data: Any) -> list[dict[str, Any]]:
    """Accept the documented response shape and a few defensive variants."""
    if isinstance(data, dict):
        for key in ("data", "mods", "results", "matches"):
            value = data.get(key)
            if isinstance(value, list):
                data = value
                break
        else:
            data = []
    if not isinstance(data, list):
        return []

    matches: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        mod = item.get("mod") if isinstance(item.get("mod"), dict) else item
        file_obj = item.get("file") if isinstance(item.get("file"), dict) else {}
        mod_id_raw = mod.get("mod_id") or mod.get("id")
        try:
            mod_id = int(mod_id_raw) if mod_id_raw not in (None, "") else None
        except (TypeError, ValueError):
            mod_id = None
        matches.append(
            {
                "mod_id": mod_id,
                "mod_name": mod.get("name") or "",
                "file_name": file_obj.get("name") or mod.get("file_name") or "",
                "version": file_obj.get("version") or mod.get("version") or "",
                "file_id": file_obj.get("file_id"),
                "mod_url": (
                    f"https://www.nexusmods.com/{GAME_DOMAIN}/mods/{mod_id}"
                    if mod_id
                    else ""
                ),
            }
        )
    return matches
