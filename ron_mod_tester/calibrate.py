from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import psutil

from . import APP_NAME
from .proc import (
    click_window,
    close_error_windows,
    find_game_main_windows,
    find_game_processes,
    graceful_close,
    launch_game,
)


def calibrate(
    exe_path: Path,
    extra_args: str,
    *,
    startup_timeout: int = 180,
    max_seconds: int = 120,
    emit_log: Callable[[str], Any] | None = None,
    cancel_event: Any = None,
) -> dict[str, Any]:
    """Launch the game once and estimate how long it takes to reach the menu.

    Returns timings and a suggested ``stable_seconds`` value. Detection uses the
    main-window appearance plus a short CPU-idle period (the menu is usually idle
    compared with loading). If idle is never observed, a conservative fallback is
    returned.
    """
    emit = emit_log or (lambda _s: None)
    proc = launch_game(exe_path, "", extra_args)
    if proc is None:
        raise RuntimeError("无法启动游戏进程。")

    emit(f"已启动游戏（PID {proc.pid}），开始自动测时…")
    start = time.monotonic()
    window_at: float | None = None
    idle_at: float | None = None
    last_click = start
    last_cpu_sample = start
    cpu_proc: psutil.Process | None = None
    cpu_first = True
    cpu_values: list[float] = []

    try:
        while not (cancel_event and cancel_event.is_set()):
            now = time.monotonic()
            procs = find_game_processes(exe_path)
            alive = bool(procs)
            main_windows = find_game_main_windows(procs)

            if main_windows and window_at is None:
                window_at = now
                emit(f"  游戏主窗口出现，耗时 {window_at - start:.1f}s")

            if main_windows and window_at is not None and now - last_click >= 1.0:
                click_window(main_windows[0][0])
                last_click = now

            if procs and main_windows and now - last_cpu_sample >= 1.0:
                last_cpu_sample = now
                try:
                    if cpu_proc is None:
                        cpu_proc = procs[0]
                        cpu_proc.cpu_percent(interval=None)
                        cpu_first = True
                        cpu = 0.0
                    else:
                        cpu = cpu_proc.cpu_percent(interval=None)
                    if not cpu_first:
                        cpu_values.append(cpu)
                    cpu_first = False
                    if len(cpu_values) >= 5:
                        avg = sum(cpu_values[-5:]) / 5
                        if avg < 8.0:
                            if idle_at is None:
                                idle_at = now
                                emit(f"  检测到游戏进入空闲(主菜单)，耗时 {idle_at - start:.1f}s")
                            if now - idle_at >= 5:
                                break
                        else:
                            idle_at = None
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    idle_at = None

            if not alive:
                if window_at is None and now - start >= startup_timeout:
                    raise RuntimeError(f"测时超时：{startup_timeout}s 内未出现游戏窗口。")
                if window_at is not None:
                    raise RuntimeError("测时过程中游戏异常退出，可能崩溃。")

            if now - start >= max_seconds:
                emit(f"  已达 {max_seconds}s 测时上限，使用保守建议值。")
                break

            time.sleep(0.5)
    finally:
        procs = find_game_processes(exe_path)
        if procs:
            graceful_close(procs, timeout=6)
        close_error_windows(ignore_titles=(APP_NAME,))

    t_window = round(window_at - start, 1) if window_at else None
    t_idle = round(idle_at - start, 1) if idle_at else None

    if t_idle is not None and t_window is not None:
        suggested = max(35, int(t_idle - t_window + 8))
    elif t_window is not None:
        suggested = max(35, int(t_window + 15))
    else:
        suggested = 35

    return {
        "window_seconds": t_window,
        "idle_seconds": t_idle,
        "suggested_stable": suggested,
    }
