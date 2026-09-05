from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class RepakBackend:
    """Pak backend backed by the ``repak`` CLI."""

    name = "repak"

    def __init__(self, repak_exe: str | Path | None = None) -> None:
        self.repak_exe = self._resolve_exe(repak_exe)

    @staticmethod
    def _resolve_exe(repak_exe: str | Path | None) -> Path:
        if repak_exe:
            candidate = Path(repak_exe)
            if candidate.is_file():
                return candidate
            raise FileNotFoundError(f"repak 可执行文件不存在：{candidate}")
        env = os.environ.get("REPAK_EXE")
        if env:
            candidate = Path(env)
            if candidate.is_file():
                return candidate
        found = shutil.which("repak")
        if found:
            return Path(found)
        raise FileNotFoundError(
            "找不到 repak。请用 --repak-exe 指定路径，或设置 REPAK_EXE 环境变量。"
        )

    def _run(self, args: list[str], pak: Path, timeout: int = 120) -> str:
        try:
            proc = subprocess.run(
                [str(self.repak_exe), *args, str(pak)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"repak 处理超时：{pak.name}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"repak 处理失败：{pak.name} {detail}")
        return proc.stdout

    def info(self, pak: Path) -> dict[str, object]:
        text = self._run(["info"], pak)
        result: dict[str, object] = {}
        for line in text.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                result[key.strip()] = value.strip()
        result["file_entries"] = next(
            (
                int(line.split()[0])
                for line in text.splitlines()
                if "file entries" in line and line.split()[0].isdigit()
            ),
            0,
        )
        return result

    def list_paths(self, pak: Path) -> list[str]:
        text = self._run(["list"], pak)
        return [line.strip() for line in text.splitlines() if line.strip()]

    def read_file(self, pak: Path, internal_path: str) -> bytes:
        try:
            proc = subprocess.run(
                [str(self.repak_exe), "get", str(pak), internal_path],
                capture_output=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"repak get 超时：{pak.name} {internal_path}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"repak get 失败：{pak.name} {internal_path} {detail}")
        return proc.stdout
