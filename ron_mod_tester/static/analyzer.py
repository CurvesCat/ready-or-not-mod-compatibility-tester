from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..safety import is_mod_pak
from .models import Conflict, ConflictProvider, PakFileEntry, PakInventory, StaticAnalysis
from .pak_repak import RepakBackend


def _iter_paks(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise FileNotFoundError(f"Mod 文件夹不存在：{folder}")
    paks = [
        p
        for p in folder.rglob("*.pak")
        if p.is_file() and is_mod_pak(p.name)
    ]
    # Do not descend into report/backup folders produced by the tool itself.
    paks = [
        p
        for p in paks
        if not any(
            part.endswith("_test_reports")
            or part.endswith("_static_reports")
            or part == "quarantine"
            for part in p.parts
        )
    ]
    return sorted(paks, key=lambda p: str(p).lower())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def analyze_folder(
    folder: Path,
    repak_exe: str | Path | None = None,
    log: Callable[[str], None] | None = None,
    only_paks: list[Path] | None = None,
) -> StaticAnalysis:
    """Scan every non-system pak in ``folder`` and detect path conflicts."""

    def emit(text: str) -> None:
        if log:
            log(text)

    backend = RepakBackend(repak_exe)
    if only_paks is not None:
        paks = [
            pak
            for pak in only_paks
            if pak.is_file() and is_mod_pak(pak.name)
        ]
        paks = sorted(paks, key=lambda p: str(p).lower())
    else:
        paks = _iter_paks(folder)
    emit(f"检测到 {len(paks)} 个非系统 .pak")

    inventories: list[PakInventory] = []
    warnings: list[str] = []
    provider_by_path: dict[str, list[tuple[Path, str]]] = {}

    for index, pak in enumerate(paks, start=1):
        try:
            info = backend.info(pak)
            paths = backend.list_paths(pak)
        except RuntimeError as exc:
            warnings.append(str(exc))
            inventories.append(
                PakInventory(
                    pak_path=pak,
                    filename=pak.name,
                    size_bytes=pak.stat().st_size,
                    parse_ok=False,
                    parse_error=str(exc),
                )
            )
            continue

        entries = [PakFileEntry(internal_path=path) for path in paths]
        inventory = PakInventory(
            pak_path=pak,
            filename=pak.name,
            size_bytes=pak.stat().st_size,
            mount_point=str(info.get("mount point", "")),
            pak_version=str(info.get("version", "")),
            backend=backend.name,
            entry_count=len(paths),
            entries=entries,
        )
        inventories.append(inventory)
        for path in paths:
            provider_by_path.setdefault(path, []).append((pak, pak.name))
        emit(f"  [{index}/{len(paks)}] {pak.name}: {len(paths)} 个条目")

    conflicts: list[Conflict] = []
    shared_paths = sorted(
        (path for path, providers in provider_by_path.items() if len(providers) > 1),
        key=lambda s: s.lower(),
    )
    emit(f"发现 {len(shared_paths)} 个被多个 Mod 提供的内部路径，正在对比内容…")

    for path in shared_paths:
        providers = provider_by_path[path]
        provider_records: list[ConflictProvider] = []
        hashes: set[str] = set()
        for pak, filename in providers:
            content_hash: str | None = None
            try:
                data = backend.read_file(pak, path)
                content_hash = _sha256(data)
            except RuntimeError as exc:
                warnings.append(f"{filename} 读取 {path} 失败：{exc}")
            provider_records.append(
                ConflictProvider(filename=filename, sha256=content_hash)
            )
            if content_hash:
                hashes.add(content_hash)
        kind = "duplicate" if len(hashes) == 1 else "overwrite"
        conflicts.append(Conflict(path, provider_records, kind))

    return StaticAnalysis(
        mod_folder=folder.resolve(),
        paks=inventories,
        conflicts=conflicts,
        backend=backend.name,
        created_at=datetime.now().isoformat(timespec="seconds"),
        warnings=warnings,
    )
