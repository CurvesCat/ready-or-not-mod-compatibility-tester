from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any


_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class UAssetCliReader:
    """Parse cooked .uasset/.uexp files with the UAssetCLI worker."""

    def __init__(
        self,
        dotnet_exe: str | Path,
        uasset_cli_dll: str | Path,
        engine: str = "VER_UE5_4",
        timeout: int = 60,
    ) -> None:
        self.dotnet_exe = Path(dotnet_exe)
        self.uasset_cli_dll = Path(uasset_cli_dll)
        self.engine = engine
        self.timeout = timeout

    def _run(
        self,
        uasset_path: Path,
        uexp_path: Path | None,
        out_json: Path,
    ) -> dict[str, Any]:
        if not self.dotnet_exe.is_file():
            raise FileNotFoundError(f"dotnet 可执行文件不存在：{self.dotnet_exe}")
        if not self.uasset_cli_dll.is_file():
            raise FileNotFoundError(f"UAssetCLI.dll 不存在：{self.uasset_cli_dll}")
        try:
            proc = subprocess.run(
                [
                    str(self.dotnet_exe),
                    str(self.uasset_cli_dll),
                    "tojson",
                    str(uasset_path),
                    str(out_json),
                    self.engine,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
                creationflags=_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"UAssetCLI 超时：{uasset_path.name}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(
                f"UAssetCLI 解析失败：{uasset_path.name} {detail}"
            )
        if not out_json.is_file():
            raise RuntimeError(f"UAssetCLI 未生成 JSON：{uasset_path.name}")
        try:
            return json.loads(out_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"UAssetCLI JSON 读取失败：{uasset_path.name} {exc}") from exc

    def parse_file(
        self,
        uasset_path: Path,
        uexp_path: Path | None,
        temp_root: Path,
    ) -> dict[str, Any]:
        out_json = temp_root / f"asset_{uuid.uuid4().hex}.json"
        try:
            return self._run(uasset_path, uexp_path, out_json)
        finally:
            try:
                if out_json.exists():
                    out_json.unlink()
            except OSError:
                pass


def find_dotnet_default() -> Path | None:
    env = os.environ.get("DOTNET_EXE")
    if env:
        candidate = Path(env)
        if candidate.is_file():
            return candidate
    return None
