from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Verdict(str, Enum):
    OK = "可用"
    FAIL = "不可用"
    ERROR = "错误"
    CONFLICT = "已存在"
    SKIPPED = "跳过"


@dataclass
class GameInfo:
    root: Path
    exe: Path
    paks_dir: Path
    mod_dir_candidates: list[Path] = field(default_factory=list)
    log_dir: Path | None = None
    crashes_dir: Path | None = None

    @property
    def steam_app_id(self) -> str:
        return "1144200"


@dataclass
class AppConfig:
    mod_folder: Path | None = None
    mod_files: list[Path] = field(default_factory=list)
    exclude_files: list[Path] = field(default_factory=list)
    game_root: Path | None = None
    exe_path: Path | None = None
    mod_dir: Path | None = None
    report_dir: Path | None = None
    mode: str = "isolated"  # "isolated" | "strict"
    stable_seconds: int = 35
    startup_timeout: int = 120
    menu_hold_seconds: int = 6
    close_timeout: int = 6
    close_running: bool = True
    backup_mods: bool = True
    backup_dir: Path | None = None
    backup_max_file_mb: int = 1500
    backup_max_total_mb: int = 10000
    source: str = "folder"  # "folder" | "installed"
    disposition: str = "quarantine"  # "quarantine" | "disable" | "delete" | "record"
    warmup: bool = False
    extra_args: str = "-windowed -nosplash"


@dataclass
class TestResult:
    filename: str
    source_path: Path
    verdict: Verdict
    elapsed_seconds: float = 0.0
    reason: str = ""
    log_excerpt: str = ""
    started_at: str = ""
    finished_at: str = ""
    deployed_path: Path | None = None
    quarantined_path: Path | None = None
    mod_dir: str = ""
    exe: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "source_path": str(self.source_path) if self.source_path else "",
            "verdict": self.verdict.value,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "reason": self.reason,
            "log_excerpt": self.log_excerpt,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "deployed_path": str(self.deployed_path) if self.deployed_path else "",
            "quarantined_path": str(self.quarantined_path) if self.quarantined_path else "",
            "mod_dir": self.mod_dir,
            "exe": self.exe,
            "details": self.details,
        }
