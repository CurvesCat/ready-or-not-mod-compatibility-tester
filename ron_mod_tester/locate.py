from __future__ import annotations

import os
import re
import winreg
from pathlib import Path

from .models import GameInfo


STEAM_APP_DIR_NAMES = ("Ready Or Not", "ReadyOrNot")
STEAM_APP_ID = "1144200"


def _registry_value(key_path: str, value_name: str) -> str | None:
    for hive, access in (
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_READ | winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_CURRENT_USER, winreg.KEY_READ),
    ):
        try:
            with winreg.OpenKey(hive, key_path, 0, access) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                if value:
                    return str(value)
        except OSError:
            continue
    return None


def _steam_install_dir() -> Path | None:
    value = _registry_value(r"SOFTWARE\Valve\Steam", "InstallPath")
    if not value:
        value = _registry_value(r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath")
    if not value:
        value = _registry_value(r"Software\Valve\Steam", "SteamPath")
    return Path(value) if value and Path(value).exists() else None


def _library_paths_from_vdf(vdf: Path) -> list[Path]:
    paths: list[Path] = []
    try:
        text = vdf.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return paths
    for match in re.finditer(r'"path"\s+"([^"]+)"', text):
        raw = match.group(1)
        raw = raw.replace("\\\\", "\\")
        p = Path(raw)
        if p.exists() and p not in paths:
            paths.append(p)
    return paths


def steam_steamapps_dirs() -> list[Path]:
    """Return every ``steamapps`` directory reachable from Steam's config."""
    dirs: list[Path] = []
    steam = _steam_install_dir()
    if steam:
        steamapps = steam / "steamapps"
        if steamapps.exists():
            dirs.append(steamapps)
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        for library in _library_paths_from_vdf(vdf):
            candidate = library / "steamapps"
            if candidate.exists() and candidate not in dirs:
                dirs.append(candidate)

    # Common fixed locations used by many people, checked as a fallback.
    fallbacks = (
        Path("C:/Program Files (x86)/Steam/steamapps"),
        Path("C:/Program Files/Steam/steamapps"),
        Path("D:/SteamLibrary/steamapps"),
        Path("E:/SteamLibrary/steamapps"),
        Path("C:/SteamLibrary/steamapps"),
    )
    for candidate in fallbacks:
        if candidate.exists() and candidate not in dirs:
            dirs.append(candidate)
    return dirs


def _looks_like_game_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    if (path / "ReadyOrNot" / "Content" / "Paks").is_dir():
        return True
    if (path / "ReadyOrNot" / "Binaries" / "Win64").is_dir():
        return True
    if (path / "ReadyOrNot.exe").is_file():
        return True
    return False


def find_game_roots() -> list[Path]:
    roots: list[Path] = []
    for steamapps in steam_steamapps_dirs():
        common = steamapps / "common"
        if not common.is_dir():
            continue
        for name in STEAM_APP_DIR_NAMES:
            candidate = common / name
            if _looks_like_game_root(candidate) and candidate not in roots:
                roots.append(candidate)
    return roots


def _choose_exe(win64_dir: Path) -> Path | None:
    if not win64_dir.is_dir():
        return None
    exes = list(win64_dir.glob("*.exe"))
    shipping = [
        p
        for p in exes
        if "shipping" in p.name.lower()
        and "readyornot" in p.name.lower()
        and "crashreport" not in p.name.lower()
        and "unrealcef" not in p.name.lower()
    ]
    # Prefer the Steam build when present (current UE5 release uses it).
    for p in shipping:
        if "steam" in p.name.lower():
            return p
    if shipping:
        return sorted(shipping, key=lambda p: p.name)[0]
    fallback = [
        p
        for p in exes
        if "readyornot" in p.name.lower() and "crashreport" not in p.name.lower()
    ]
    return fallback[0] if fallback else None


def build_game_info(root: Path) -> GameInfo | None:
    root = root.resolve()
    paks_dir = root / "ReadyOrNot" / "Content" / "Paks"
    win64_dir = root / "ReadyOrNot" / "Binaries" / "Win64"
    if not (paks_dir.is_dir() or win64_dir.is_dir()):
        return None

    exe = _choose_exe(win64_dir)

    mod_dir_candidates: list[Path] = []
    for sub in ("~mods", "~Mods", "Mods", "mods"):
        candidate = paks_dir / sub
        if candidate.is_dir():
            mod_dir_candidates.append(candidate)
    mod_dir_candidates.append(paks_dir)

    local_appdata = Path(os.environ.get("LOCALAPPDATA", "")) / "ReadyOrNot" / "Saved"
    install_saved = root / "ReadyOrNot" / "Saved"

    log_dir = None
    for candidate in (
        local_appdata / "Logs",
        install_saved / "Logs",
    ):
        if candidate.is_dir():
            log_dir = candidate
            break

    crashes_dir = None
    for candidate in (
        local_appdata / "Crashes",
        install_saved / "Crashes",
    ):
        if candidate.is_dir():
            crashes_dir = candidate
            break

    return GameInfo(
        root=root,
        exe=exe if exe else root / "ReadyOrNot" / "Binaries" / "Win64" / "ReadyOrNot-Win64-Shipping.exe",
        paks_dir=paks_dir,
        mod_dir_candidates=mod_dir_candidates,
        log_dir=log_dir,
        crashes_dir=crashes_dir,
    )


def detect_game(preferred_root: Path | None = None) -> GameInfo | None:
    if preferred_root and _looks_like_game_root(preferred_root):
        info = build_game_info(preferred_root)
        if info:
            return info
    for root in find_game_roots():
        info = build_game_info(root)
        if info:
            return info
    return None


def detect_mod_dir(info: GameInfo, preferred: Path | None = None) -> Path | None:
    if preferred and preferred.is_dir():
        return preferred
    dedicated = [
        c for c in info.mod_dir_candidates if c != info.paks_dir and c.is_dir()
    ]
    for candidate in dedicated:
        try:
            if any(candidate.iterdir()):
                return candidate
        except OSError:
            continue
    for candidate in info.mod_dir_candidates:
        if candidate.is_dir():
            return candidate
    return info.paks_dir if info.paks_dir.is_dir() else None
