from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PakFileEntry:
    """A single file inside a .pak."""

    internal_path: str
    sha256: str | None = None


@dataclass
class PakInventory:
    """Result of listing one pak."""

    pak_path: Path
    filename: str
    size_bytes: int = 0
    mount_point: str = ""
    pak_version: str = ""
    backend: str = ""
    entry_count: int = 0
    entries: list[PakFileEntry] = field(default_factory=list)
    parse_ok: bool = True
    parse_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "pak_path": str(self.pak_path),
            "size_bytes": self.size_bytes,
            "mount_point": self.mount_point,
            "pak_version": self.pak_version,
            "backend": self.backend,
            "entry_count": self.entry_count,
            "entries": [
                {"internal_path": e.internal_path, "sha256": e.sha256}
                for e in self.entries
            ],
            "parse_ok": self.parse_ok,
            "parse_error": self.parse_error,
        }


@dataclass
class ConflictProvider:
    filename: str
    sha256: str | None


@dataclass
class Conflict:
    """Two or more mods provide the same internal file path."""

    internal_path: str
    providers: list[ConflictProvider]
    kind: str  # "duplicate" | "overwrite"

    def as_dict(self) -> dict[str, Any]:
        return {
            "internal_path": self.internal_path,
            "kind": self.kind,
            "providers": [
                {"filename": p.filename, "sha256": p.sha256}
                for p in self.providers
            ],
        }


@dataclass
class StaticAnalysis:
    """T1 result: pak inventory summary + conflicts."""

    mod_folder: Path
    paks: list[PakInventory]
    conflicts: list[Conflict]
    backend: str
    created_at: str
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "ronct.static.v1",
            "backend": self.backend,
            "created_at": self.created_at,
            "mod_folder": str(self.mod_folder),
            "paks": [p.as_dict() for p in self.paks],
            "conflicts": [c.as_dict() for c in self.conflicts],
            "warnings": self.warnings,
        }
