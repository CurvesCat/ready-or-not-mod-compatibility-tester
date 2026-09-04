"""Ready or Not mod compatibility tester.

A small Windows tool that tests each .pak mod one by one by launching the game,
monitoring for crashes or errors, and producing a CSV/JSON report.
"""

APP_NAME = "RoN Mod 兼容性测试器"
VERSION = "0.1.1"
AUTHOR = "CurvesCat"


def default_backup_dir():
    """Return the default backup folder: next to the executable when frozen,
    otherwise the current working directory."""
    import sys
    from pathlib import Path

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "backup"
    return Path.cwd() / "backup"
