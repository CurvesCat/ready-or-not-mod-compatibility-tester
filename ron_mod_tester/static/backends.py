from __future__ import annotations

from pathlib import Path
from typing import Protocol


class PakLister(Protocol):
    """Common interface implemented by pak listing backends."""

    name: str

    def info(self, pak: Path) -> dict[str, object]: ...

    def list_paths(self, pak: Path) -> list[str]: ...

    def read_file(self, pak: Path, internal_path: str) -> bytes: ...
