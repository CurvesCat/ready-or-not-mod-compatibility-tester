from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import threading
from pathlib import Path


LOG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "RoNModCompatTester"
LOG_FILE = LOG_DIR / "debug.log"


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ron_mct")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_000_000,  # ~1 MB per file
            backupCount=3,       # keep 3 rotated files, then delete oldest
            encoding="utf-8",
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)


def get_logger() -> logging.Logger:
    return logging.getLogger("ron_mct")


def audit(action: str) -> None:
    """Record a user action in the log."""
    get_logger().info("USER_ACTION: %s", action)


def install_excepthook() -> None:
    def _handle_exception(exc_type, exc_value, exc_tb) -> None:
        get_logger().error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    def _handle_thread_exception(args) -> None:
        get_logger().error(
            "Uncaught exception in thread",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _handle_exception
    threading.excepthook = _handle_thread_exception
