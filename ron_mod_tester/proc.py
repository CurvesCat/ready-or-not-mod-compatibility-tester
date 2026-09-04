from __future__ import annotations

import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

import psutil


WM_CLOSE = 0x0010
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def _norm_path(path: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def find_game_processes(exe_path: str | Path) -> list[psutil.Process]:
    target = _norm_path(exe_path)
    procs: list[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "exe"]):
        try:
            exe = proc.info.get("exe")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        if exe and _norm_path(exe) == target:
            procs.append(proc)
    return procs


def _windows_for_pid(pid: int) -> list[int]:
    """Return HWNDs belonging to ``pid`` using Win32 EnumWindows."""
    hwnds: list[int] = []
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )

    def callback(hwnd: int, _lparam: int) -> bool:
        window_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value == pid:
            hwnds.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    kernel32.SetLastError(0)
    return hwnds


def post_close_windows(procs: list[psutil.Process]) -> int:
    """Send WM_CLOSE to visible top-level windows of each process."""
    user32 = ctypes.windll.user32
    count = 0
    for proc in procs:
        try:
            pid = proc.pid
        except psutil.NoSuchProcess:
            continue
        for hwnd in _windows_for_pid(pid):
            if user32.IsWindowVisible(hwnd):
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                count += 1
    return count


def _is_alive(proc: psutil.Process) -> bool:
    try:
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def graceful_close(procs: list[psutil.Process], timeout: float = 20.0) -> None:
    """Close game processes as gracefully as possible, then force-kill."""
    if not procs:
        return
    post_close_windows(procs)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(_is_alive(p) for p in procs):
            return
        time.sleep(0.25)

    children: list[psutil.Process] = []
    for proc in procs:
        try:
            children.extend(proc.children(recursive=True))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for proc in children:
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    for proc in procs:
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(1.0)
    for proc in list(children) + list(procs):
        try:
            if _is_alive(proc):
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def launch_game(
    exe_path: str | Path,
    log_path: str | Path,
    extra_args: str = "",
) -> subprocess.Popen[bytes] | None:
    args = [str(exe_path)]
    if log_path:
        args.append(f"-abslog={log_path}")
    if extra_args:
        args.extend(extra_args.split())
    try:
        return subprocess.Popen(
            args,
            cwd=str(Path(exe_path).parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None


ERROR_TITLE_PATTERNS = (
    "fatal error",
    "lowlevelfatalerror",
    "assertion failed",
    "unreal engine",
    "crash reporter",
    "stopped working",
    "has crashed",
    "ue4-",
    "ue5-",
)


def _window_texts() -> list[tuple[int, str, str]]:
    results: list[tuple[int, str, str]] = []
    user32 = ctypes.windll.user32

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        title_len = user32.GetWindowTextLengthW(hwnd)
        if title_len <= 0:
            return True
        title_buf = ctypes.create_unicode_buffer(title_len + 1)
        user32.GetWindowTextW(hwnd, title_buf, title_len + 1)
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        results.append((hwnd, title_buf.value, class_buf.value))
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return results


def _hwnd_pid(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def find_game_main_windows(
    procs: list[psutil.Process],
) -> list[tuple[int, str, str]]:
    """Return visible game main windows (UnrealWindow) belonging to ``procs``."""
    pids = set()
    for proc in procs:
        try:
            pids.add(proc.pid)
        except psutil.NoSuchProcess:
            continue
    results: list[tuple[int, str, str]] = []
    for hwnd, title, cls in _window_texts():
        if _hwnd_pid(hwnd) not in pids:
            continue
        lowered_cls = cls.lower()
        if lowered_cls == "unrealwindow":
            results.append((hwnd, title, cls))
        elif "ready or not" in title.lower() and lowered_cls != "consolewindowclass":
            results.append((hwnd, title, cls))
    return results


def click_window(hwnd: int) -> None:
    """Send a synthetic left click to ``hwnd`` to skip intro/movie screens."""
    user32 = ctypes.windll.user32
    rect = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    x = (rect.left + rect.right) // 2
    y = (rect.top + rect.bottom) // 2
    lparam = (y << 16) | (x & 0xFFFF)
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)


def find_error_windows(ignore_titles: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    """Return ``(title, class)`` pairs for visible windows that look like errors."""
    errors: list[tuple[str, str]] = []
    for _hwnd, title, cls in _window_texts():
        lowered = title.lower()
        if any(ignore.lower() in lowered for ignore in ignore_titles):
            continue
        if any(pattern in lowered for pattern in ERROR_TITLE_PATTERNS):
            errors.append((title, cls))
    return errors


def close_error_windows(ignore_titles: tuple[str, ...] = ()) -> int:
    """Post WM_CLOSE to visible windows that look like crash/error dialogs."""
    user32 = ctypes.windll.user32
    count = 0
    for hwnd, title, _cls in _window_texts():
        lowered = title.lower()
        if any(ignore.lower() in lowered for ignore in ignore_titles):
            continue
        if any(pattern in lowered for pattern in ERROR_TITLE_PATTERNS):
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            count += 1
    return count


def is_steam_running() -> bool:
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info.get("name") or "").lower()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        if name == "steam.exe":
            return True
    return False
