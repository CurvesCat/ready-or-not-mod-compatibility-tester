"""RoNCT - Ready or Not mod compatibility tester.

A small Windows tool that tests each .pak mod one by one by launching the game,
monitoring for crashes or errors, and producing a CSV/JSON report.
"""

APP_NAME = "RoN Mod 兼容性测试器"
SHORT_NAME = "RoNCT"
VERSION = "0.4.0"
AUTHOR = "CurvesCat"


def app_root() -> "Path":
    """Software directory: next to the exe in release zips, repo root in source."""
    import sys
    from pathlib import Path

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def default_backup_dir() -> "Path":
    return app_root() / "backup"


def default_reports_dir() -> "Path":
    return app_root() / "reports"
