"""GitHub-based auto-update support."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from . import VERSION, app_root

# The GitHub repository hosting release builds. Change here to point elsewhere.
REPO = "CurvesCat/ready-or-not-mod-compatibility-tester"


def _ver_tuple(version: str) -> tuple[int, int, int]:
    parts = re.findall(r"\d+", version)
    nums = [int(x) for x in parts[:3]]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])  # type: ignore[return-value]


def is_newer(latest: str, current: str = VERSION) -> bool:
    return _ver_tuple(latest) > _ver_tuple(current)


def check_for_update(repo: str = REPO, timeout: float = 15) -> dict[str, Any]:
    """Query GitHub Releases for the newest release.

    Returns a dict with ``latest`` (tag, no leading v), ``newer``, ``asset_url``,
    ``asset_name``, ``notes``, ``html_url``. Raises on network/API errors.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "RoNCT-Updater",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    latest = (data.get("tag_name") or "").lstrip("v")
    asset = None
    for item in data.get("assets", []):
        name = item.get("name", "")
        if name.lower().endswith(".zip"):
            asset = item
            break

    return {
        "latest": latest,
        "newer": bool(latest) and is_newer(latest),
        "asset_url": asset.get("browser_download_url") if asset else None,
        "asset_name": asset.get("name") if asset else None,
        "notes": data.get("body") or "",
        "html_url": data.get("html_url") or "",
    }


def download(url: str, dest_path: Path, timeout: float = 120) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "RoNCT-Updater"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    return dest_path


def updates_dir() -> Path:
    return app_root() / "updates"

