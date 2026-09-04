from __future__ import annotations

import shutil
import re
import time
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import APP_NAME
from .models import Verdict
from .proc import (
    close_error_windows,
    click_window,
    find_error_windows,
    find_game_processes,
    find_game_main_windows,
    graceful_close,
    launch_game,
)


POLL_INTERVAL = 0.25

# Common Unreal Engine main-menu markers. These are intentionally configurable
# later; the engine falls back to a fixed stable window when none are seen.
MENU_MARKERS = (
    "loading 'l_mainmenu",
    "loaded 'l_mainmenu",
    "l_mainmenu",
    "mainmenu",
    "main menu",
    "loading 'mainmenu",
    "loaded 'mainmenu",
)

FATAL_MARKERS = (
    "fatal error",
    "lowlevelfatalerror",
    "assertion failed",
    "unhandled exception",
    "critical error",
    "exception_access_violation",
    "the application crashed",
    "apperror",
)

# Strong signs that a loose .pak failed to load, even if the game itself
# still reaches the menu. These are common UE log prefixes.
MOD_ERROR_MARKERS = (
    "logpakfile: error",
    "failed to mount",
    "loglinker: error",
    "logstreaming: error",
    "loguobjectglobals: error",
    "logclass: error",
)


@dataclass
class DeployItem:
    source: Path
    target_name: str
    target_path: Path | None = None


@dataclass
class SessionResult:
    verdict: Verdict
    reason: str = ""
    excerpt: str = ""
    menu_reached: bool = False
    elapsed_seconds: float = 0.0
    crash_dirs: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.verdict == Verdict.OK


def _decode_log(data: bytes) -> str:
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def _scan_log(
    log_path: Path,
    offset: int,
    tail_lines: list[str],
) -> tuple[int, list[str], str | None, bool]:
    """Return ``(new_offset, tail_lines, fatal_snippet, menu_found)``."""
    if not log_path or not log_path.exists():
        return offset, tail_lines, None, False
    try:
        data = log_path.read_bytes()
    except OSError:
        return offset, tail_lines, None, False
    if len(data) <= offset:
        return offset, tail_lines, None, False

    new_text = _decode_log(data[offset:])
    new_offset = len(data)
    lines = new_text.splitlines()
    tail_lines = (tail_lines + lines)[-25:]

    lowered = new_text.lower()
    fatal_snippet = None
    for marker in FATAL_MARKERS + MOD_ERROR_MARKERS:
        idx = lowered.find(marker)
        if idx >= 0:
            start = max(0, idx - 200)
            end = min(len(new_text), idx + 400)
            fatal_snippet = new_text[start:end].strip()
            break

    menu_found = any(marker in lowered for marker in MENU_MARKERS)
    return new_offset, tail_lines, fatal_snippet, menu_found


def _new_crash_dirs(crashes_dir: Path | None, before: set[str]) -> list[str]:
    if not crashes_dir or not crashes_dir.is_dir():
        return []
    try:
        after = {p.name for p in crashes_dir.iterdir() if p.is_dir()}
    except OSError:
        return []
    return sorted(after - before)


class GameSession:
    """Deploy some mods, launch the game once, observe, then restore."""

    def __init__(
        self,
        *,
        exe_path: Path,
        mod_dir: Path,
        log_dir: Path,
        crashes_dir: Path | None,
        stable_seconds: int,
        startup_timeout: int,
        menu_hold_seconds: int,
        close_timeout: int,
        extra_args: str,
        emit_log: Any,
        cancel_event: Any,
    ) -> None:
        self.exe_path = exe_path
        self.mod_dir = mod_dir
        self.log_dir = log_dir
        self.crashes_dir = crashes_dir
        self.stable_seconds = stable_seconds
        self.startup_timeout = startup_timeout
        self.menu_hold_seconds = menu_hold_seconds
        self.close_timeout = close_timeout
        self.extra_args = extra_args
        self.emit_log = emit_log
        self.cancel_event = cancel_event
        self._items: list[DeployItem] = []

    def run(self, items: list[DeployItem], label: str) -> SessionResult:
        self._items = items
        self._session_counter = getattr(self, "_session_counter", 0) + 1
        safe_label = f"session_{int(time.time())}_{self._session_counter}"
        for item in items:
            item.target_path = self.mod_dir / item.target_name
            if item.target_path.exists():
                return SessionResult(
                    Verdict.CONFLICT,
                    reason=f"Mod 目录中已存在同名文件：{item.target_name}",
                )

        deployed: list[Path] = []
        for item in items:
            try:
                shutil.copy2(item.source, item.target_path)
                deployed.append(item.target_path)
            except OSError as exc:
                for path in deployed:
                    self._remove(path)
                return SessionResult(
                    Verdict.ERROR,
                    reason=f"复制 Mod 到游戏目录失败：{exc}",
                )

        log_path = self.log_dir / f"{safe_label}.log"
        crash_baseline = self._crash_baseline()
        result = self._launch_and_monitor(log_path, crash_baseline)

        for path in deployed:
            self._remove(path)
        self._items = []
        return result

    def cleanup(self) -> None:
        """Best-effort cleanup used when a session is interrupted unexpectedly."""
        procs = find_game_processes(self.exe_path)
        if procs:
            graceful_close(procs, timeout=self.close_timeout)
        close_error_windows(ignore_titles=(APP_NAME,))
        for item in self._items:
            if item.target_path:
                self._remove(item.target_path)
        self._items = []

    def _remove(self, path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    def _crash_baseline(self) -> set[str]:
        if not self.crashes_dir or not self.crashes_dir.is_dir():
            return set()
        try:
            return {p.name for p in self.crashes_dir.iterdir() if p.is_dir()}
        except OSError:
            return set()

    def _launch_and_monitor(
        self, log_path: Path, crash_baseline: set[str]
    ) -> SessionResult:
        proc = launch_game(self.exe_path, log_path, self.extra_args)
        if proc is None:
            return SessionResult(Verdict.ERROR, reason="无法启动游戏进程。")

        self.emit_log(f"  已启动游戏（PID {proc.pid}）…")
        start = time.monotonic()
        startup_deadline = start + self.startup_timeout
        window_at: float | None = None
        menu_at: float | None = None
        stable_deadline: float | None = None
        last_obs_log = start
        last_click = start
        clicks = 0
        click_logged = False
        main_hwnd: int | None = None
        tail_lines: list[str] = []
        log_offset = 0

        while not self.cancel_event.is_set():
            procs = find_game_processes(self.exe_path)
            alive = bool(procs)
            now = time.monotonic()
            main_windows = find_game_main_windows(procs)

            if main_windows and window_at is None:
                window_at = now
                stable_deadline = now + self.stable_seconds
                main_hwnd = main_windows[0][0]
                self.emit_log("  游戏主窗口已出现，开始观察…")

            if (
                window_at is not None
                and main_windows
                and now - window_at >= 2.0
                and now - last_click >= 1.0
                and main_hwnd is not None
            ):
                click_window(main_hwnd)
                clicks += 1
                last_click = now
                if not click_logged:
                    self.emit_log("  开始持续点击跳过启动动画…")
                    click_logged = True

            if window_at is not None and menu_at is None and now - last_obs_log >= 10:
                waited = int(now - window_at)
                self.emit_log(f"  观察中… 已等待 {waited}s / {self.stable_seconds}s")
                last_obs_log = now

            error_windows = find_error_windows(ignore_titles=(APP_NAME,))
            if error_windows:
                titles = "；".join(t for t, _ in error_windows[:3])
                return self._finish(
                    log_path,
                    Verdict.FAIL,
                    "检测到错误弹窗：" + titles,
                    "",
                    start,
                )

            log_offset, tail_lines, fatal_snippet, menu_found = _scan_log(
                log_path, log_offset, tail_lines
            )
            if fatal_snippet:
                return self._finish(
                    log_path,
                    Verdict.FAIL,
                    "游戏日志出现致命/加载错误",
                    fatal_snippet,
                    start,
                )
            if menu_found and menu_at is None:
                menu_at = now
                self.emit_log("  检测到主菜单/引擎就绪标记，进入短确认窗口…")

            new_crash = _new_crash_dirs(self.crashes_dir, crash_baseline)
            if new_crash:
                return self._finish(
                    log_path,
                    Verdict.FAIL,
                    "生成崩溃报告：" + ", ".join(new_crash),
                    "\n".join(tail_lines[-12:]),
                    start,
                    crash_dirs=new_crash,
                )

            if not alive:
                if window_at is None:
                    if now >= startup_deadline:
                        return self._finish(
                            log_path,
                            Verdict.ERROR,
                            f"启动超时（{self.startup_timeout}s）或游戏进程未出现。",
                            "",
                            start,
                        )
                else:
                    return self._finish(
                        log_path,
                        Verdict.FAIL,
                        f"游戏启动后 {now - window_at:.1f}s 异常退出，疑似崩溃。",
                        "\n".join(tail_lines[-12:]),
                        start,
                    )
            else:
                if window_at is None:
                    if now >= startup_deadline:
                        return self._finish(
                            log_path,
                            Verdict.ERROR,
                            f"游戏进程存在，但 {self.startup_timeout}s 内未出现主窗口（可能卡在加载）。",
                            "",
                            start,
                        )
                elif menu_at is not None:
                    if now - menu_at >= self.menu_hold_seconds:
                        return self._finish(
                            log_path,
                            Verdict.OK,
                            "主菜单标记出现后保持稳定",
                            "\n".join(tail_lines[-12:]),
                            start,
                            menu_reached=True,
                        )
                elif stable_deadline is not None and now >= stable_deadline:
                    if main_windows:
                        return self._finish(
                            log_path,
                            Verdict.OK,
                            "游戏主窗口保持稳定",
                            "\n".join(tail_lines[-12:]),
                            start,
                        )
                    # Window disappeared while the process is still alive; keep
                    # waiting a little longer in case it is re-creating it.

            time.sleep(POLL_INTERVAL)

        return self._finish(
            log_path,
            Verdict.SKIPPED,
            "用户取消",
            "",
            start,
        )

    def _finish(
        self,
        log_path: Path,
        verdict: Verdict,
        reason: str,
        excerpt: str,
        start: float,
        *,
        menu_reached: bool = False,
        crash_dirs: list[str] | None = None,
    ) -> SessionResult:
        procs = find_game_processes(self.exe_path)
        if procs:
            graceful_close(procs, timeout=self.close_timeout)
        close_error_windows(ignore_titles=(APP_NAME,))
        time.sleep(0.2)
        return SessionResult(
            verdict=verdict,
            reason=reason,
            excerpt=excerpt.strip(),
            menu_reached=menu_reached,
            elapsed_seconds=round(time.monotonic() - start, 2),
            crash_dirs=crash_dirs or [],
        )
