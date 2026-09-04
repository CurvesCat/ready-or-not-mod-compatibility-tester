from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


SYSTEM_PAK_RE = re.compile(
    r"^pakchunk\d+-Windows(?:NoEditor)?(?:_.*)?\.(?:pak|sig|ucas|utoc)$",
    re.IGNORECASE,
)


def is_system_pak(name: str) -> bool:
    return bool(SYSTEM_PAK_RE.match(name))


def is_mod_pak(name: str) -> bool:
    return name.lower().endswith(".pak") and not is_system_pak(name)


def _safe_basename(name: str) -> bool:
    """Reject names that could escape a directory (.., separators, empty)."""
    if not name or name in (".", ".."):
        return False
    if "/" in name or "\\" in name:
        return False
    if ".." in name:
        return False
    return True


def list_mod_paks(folder: Path, exclude: Path | None = None) -> list[Path]:
    """Return non-system ``.pak`` files in ``folder``, searching subfolders too."""
    if not folder or not folder.is_dir():
        return []
    root = folder.resolve()
    items = [
        p
        for p in folder.rglob("*.pak")
        if p.is_file() and is_mod_pak(p.name)
    ]
    # Never follow junctions/symlinks that escape the chosen folder, so later
    # quarantine/delete operations can never touch files outside it.
    items = [
        p
        for p in items
        if root in p.resolve().parents or p.resolve().parent == root
    ]
    if exclude is not None:
        excluded = exclude.resolve()
        items = [
            p
            for p in items
            if excluded not in p.resolve().parents and p.resolve() != excluded
        ]
    return sorted(items, key=lambda p: str(p).lower())


def _file_stat(path: Path) -> dict[str, object]:
    try:
        st = path.stat()
    except OSError:
        return {"size": -1, "mtime": -1}
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def snapshot_mod_dir(mod_dir: Path) -> dict[str, dict[str, object]]:
    """Record top-level file names and metadata so we can verify nothing changed."""
    snapshot: dict[str, dict[str, object]] = {}
    if not mod_dir or not mod_dir.is_dir():
        return snapshot
    for p in mod_dir.iterdir():
        if p.is_file():
            snapshot[p.name] = _file_stat(p)
        else:
            snapshot[p.name + "/"] = {"dir": True}
    return snapshot


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(
    mod_dir: Path,
    backup_root: Path,
    *,
    backup_enabled: bool,
    max_file_bytes: int = 1_500_000_000,
    max_total_bytes: int = 10_000_000_000,
) -> tuple[Path, Path]:
    """Create a single reusable backup folder plus a state manifest.

    The manifest always records the pre-test state. When ``backup_enabled`` is
    true we additionally copy non-system ``.pak`` files (i.e. already-installed
    mods) as long as the configured size limits allow it. Game system paks such
    as ``pakchunk0-Windows.pak`` are intentionally never copied.
    """
    backup_dir = backup_root
    backup_dir.mkdir(parents=True, exist_ok=True)

    if backup_enabled:
        # Remove previous copied non-system paks so the backup never goes stale.
        for old in backup_dir.iterdir():
            if old.is_file() and is_mod_pak(old.name):
                try:
                    old.unlink()
                except OSError:
                    pass

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "mod_dir": str(mod_dir),
        "backup_enabled": backup_enabled,
        "files": {},
    }

    if not mod_dir.is_dir():
        (backup_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return backup_dir, backup_dir / "manifest.json"

    total = 0
    for p in sorted(mod_dir.iterdir()):
        if p.is_file():
            if not _safe_basename(p.name):
                continue
            stat = _file_stat(p)
            manifest["files"][p.name] = {
                "size": stat["size"],
                "mtime": stat["mtime"],
                "sha256": None,
            }
            size = int(stat["size"])
            if (
                backup_enabled
                and is_mod_pak(p.name)
                and size <= max_file_bytes
                and total + size <= max_total_bytes
            ):
                try:
                    shutil.copy2(p, backup_dir / p.name)
                    manifest["files"][p.name]["sha256"] = _sha256(p)
                    total += size
                except OSError as exc:
                    manifest["files"][p.name]["copy_error"] = str(exc)
        else:
            manifest["files"][p.name + "/"] = {"dir": True}

    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return backup_dir, manifest_path


def restore_backup(
    backup_dir: Path,
    mod_dir: Path,
    *,
    remove_new: bool = False,
) -> tuple[list[str], list[str]]:
    """Restore non-system ``.pak`` files from ``backup_dir`` into ``mod_dir``.

    Returns ``(restored_names, removed_names)``. When ``remove_new`` is true,
    non-system ``.pak`` files currently in ``mod_dir`` that were not recorded in
    the backup manifest are removed, making this a complete rollback.
    """
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"未找到备份清单：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored: list[str] = []
    for name, meta in manifest.get("files", {}).items():
        if meta.get("dir"):
            continue
        if not _safe_basename(name):
            continue
        source = backup_dir / name
        if source.is_file():
            try:
                shutil.copy2(source, mod_dir / name)
                restored.append(name)
            except OSError:
                continue

    removed: list[str] = []
    if remove_new and mod_dir.is_dir():
        known = set(manifest.get("files", {}).keys())
        for p in mod_dir.iterdir():
            if p.is_file() and is_mod_pak(p.name) and p.name not in known:
                try:
                    p.unlink()
                    removed.append(p.name)
                except OSError:
                    continue
    return restored, removed


def verify_dir_state(
    mod_dir: Path, before: dict[str, dict[str, object]]
) -> list[str]:
    """Return human-readable differences between ``before`` and current state."""
    after = snapshot_mod_dir(mod_dir)
    diffs: list[str] = []
    for name in sorted(set(before) | set(after)):
        if name not in before:
            diffs.append(f"新增: {name}")
        elif name not in after:
            diffs.append(f"缺失: {name}")
        else:
            b = before[name]
            a = after[name]
            if b.get("dir") or a.get("dir"):
                if bool(b.get("dir")) != bool(a.get("dir")):
                    diffs.append(f"类型变化: {name}")
                continue
            if b.get("size") != a.get("size"):
                diffs.append(f"大小变化: {name}")
    return diffs
