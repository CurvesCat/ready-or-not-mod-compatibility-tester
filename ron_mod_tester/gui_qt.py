"""RoNCT v0.4 modern GUI (PySide6, Windows 11 Fluent look).

Keeps the existing Python engine untouched; only replaces the outer shell.
Theme follows the Windows app theme automatically.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QVariantAnimation
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import (
    APP_NAME,
    SHORT_NAME,
    VERSION,
    AUTHOR,
    app_root,
    default_backup_dir,
    default_reports_dir,
)
from .i18n import set_language, t as _t
from .locate import detect_game, detect_mod_dir
from .log import LOG_FILE, audit, get_logger, install_excepthook, setup_logging
from .models import AppConfig
from .safety import is_mod_pak, list_mod_paks, restore_backup

CONFIG_PATH = app_root()
CONFIG_FILE = CONFIG_PATH / "config.json"
LEGACY_CONFIG_FILE = (
    Path(os.environ.get("APPDATA", str(Path.home())))
    / "RoNModCompatTester"
    / "config.json"
)
GITHUB_URL = "https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester"
NEXUS_KEY_URL = "https://www.nexusmods.com/settings/api-keys"
CONTACT_EMAIL = "ronct.dev@icloud.com"
RAW_LICENSE_URL = (
    "https://raw.githubusercontent.com/CurvesCat/"
    "ready-or-not-mod-compatibility-tester/main/LICENSE"
)
DISPOSITIONS = ["quarantine", "disable", "delete", "record"]

THEME_LIGHT = {
    "bg": "#F3F3F3",
    "card": "#FFFFFF",
    "cardAlt": "#F9F9F9",
    "border": "#E4E4E4",
    "field": "#FFFFFF",
    "fieldBorder": "#8B8B8B",
    "text": "#1A1A1A",
    "secondary": "#424242",
    "tertiary": "#6F6F6F",
    "accent": "#005FB8",
    "accentHover": "#0B6AC7",
    "onAccent": "#FFFFFF",
    "link": "#005FB8",
    "activeBg": "#E9E9E9",
    "navHover": "#0D000000",
    "success": "#0F7B0F",
    "successBg": "#E9F5E9",
    "danger": "#C42B1C",
    "dangerBg": "#FDE9E7",
    "warn": "#9D5D00",
    "warnBg": "#FFF4CE",
    "gray": "#6E6E73",
    "scroll": "#C7C7C7",
    "scrollHover": "#A0A0A0",
}

THEME_DARK = {
    "bg": "#202020",
    "card": "#2B2B2B",
    "cardAlt": "#333333",
    "border": "#3B3B3B",
    "field": "#333333",
    "fieldBorder": "#626262",
    "text": "#FFFFFF",
    "secondary": "#C2C2C2",
    "tertiary": "#8D8D8D",
    "accent": "#4CC2FF",
    "accentHover": "#6DD3FF",
    "onAccent": "#0A0A0A",
    "link": "#60CDFF",
    "activeBg": "#3B3B3B",
    "navHover": "#0DFFFFFF",
    "success": "#6CCB5F",
    "successBg": "#243A24",
    "danger": "#FF99A4",
    "dangerBg": "#3B2428",
    "warn": "#FFD27A",
    "warnBg": "#3B3220",
    "gray": "#A1A1A6",
    "scroll": "#4A4A4A",
    "scrollHover": "#5F5F5F",
}


def fluent_qss(dark: bool) -> str:
    t = THEME_DARK if dark else THEME_LIGHT
    return f"""
* {{
    font-family: "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI",
                 "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
    font-size: 14px;
    color: {t["text"]};
}}
QWidget#root {{ background: {t["bg"]}; }}
QWidget#navPane {{ background: {t["bg"]}; border-right: 1px solid {t["border"]}; }}
QScrollArea {{ border: none; background: transparent; }}
QWidget#page, QWidget#content {{ background: transparent; }}

QLabel#navBrand {{ font-size: 15px; font-weight: 600; color: {t["text"]}; }}
QLabel#navHint {{ font-size: 11px; color: {t["tertiary"]}; }}
QLabel#heroTitle {{
    font-size: 28px; font-weight: 600; color: {t["text"]};
}}
QLabel#heroSub {{ font-size: 14px; color: {t["secondary"]}; }}

QPushButton#navItem {{
    background: transparent; border: none; border-radius: 6px;
    text-align: left; padding: 9px 14px; font-size: 13px;
    color: {t["secondary"]};
}}
QPushButton#navItem:hover {{ background: {t["navHover"]}; color: {t["text"]}; }}
QPushButton#navActive {{
    background: {t["activeBg"]}; border: none; border-radius: 6px;
    text-align: left; padding: 9px 14px; font-size: 13px; font-weight: 600;
    color: {t["text"]};
}}
QPushButton#langBtn {{
    background: transparent; border: 1px solid {t["border"]};
    border-radius: 6px; padding: 6px 10px; font-size: 12px;
    color: {t["secondary"]};
}}
QPushButton#langBtn:hover {{ background: {t["navHover"]}; color: {t["text"]}; }}

QFrame#card {{
    background: {t["card"]}; border: 1px solid {t["border"]};
    border-radius: 8px;
}}
QLabel#cardTitle {{ font-size: 16px; font-weight: 600; color: {t["text"]}; }}
QLabel#cardDesc, QLabel#hint, QLabel#dim {{ font-size: 13px; color: {t["secondary"]}; }}
QLabel#dim {{ color: {t["tertiary"]}; font-size: 12px; }}
QLabel#installedHint {{
    background: {t["accent"]}; color: {t["onAccent"]};
    border-radius: 4px; padding: 4px 8px; font-size: 12px;
}}

QLineEdit#pathEdit, QLineEdit#plainEdit, QSpinBox, QComboBox {{
    background: {t["field"]}; border: 1px solid {t["fieldBorder"]};
    border-radius: 4px; padding: 7px 10px; color: {t["text"]};
    selection-background-color: {t["accent"]};
}}
QLineEdit#pathEdit:focus, QLineEdit#plainEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {t["accent"]};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {t["card"]}; border: 1px solid {t["fieldBorder"]};
    color: {t["text"]}; selection-background-color: {t["activeBg"]};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: transparent; border: none; width: 16px;
}}

QPushButton {{
    border: none; border-radius: 6px; padding: 8px 16px; font-weight: 500;
    min-height: 20px;
}}
QPushButton#primary {{
    background: {t["accent"]}; color: {t["onAccent"]}; font-size: 15px;
    font-weight: 600; padding: 12px 34px;
}}
QPushButton#primary:hover {{ background: {t["accentHover"]}; }}
QPushButton#primary:disabled {{ background: {t["scroll"]}; color: {t["tertiary"]}; }}
QPushButton#secondary {{
    background: {t["card"]}; color: {t["text"]};
    border: 1px solid {t["fieldBorder"]};
}}
QPushButton#secondary:hover {{ background: {t["navHover"]}; }}
QPushButton#secondary:disabled {{
    color: {t["tertiary"]}; border-color: {t["border"]};
}}
QPushButton#linkBtn {{
    background: transparent; color: {t["link"]}; border: none;
    padding: 4px 6px; font-size: 13px;
}}
QPushButton#linkBtn:hover {{ text-decoration: underline; }}
QPushButton#dangerBtn {{
    background: transparent; color: {t["danger"]}; border: none;
    padding: 8px 16px;
}}

QProgressBar#prog {{
    background: {t["cardAlt"]}; border: none; border-radius: 3px;
    height: 5px; text-align: center; color: transparent;
}}
QProgressBar#prog::chunk {{
    background: {t["accent"]}; border-radius: 3px;
}}

QFrame#statTile {{
    background: {t["card"]}; border: 1px solid {t["border"]}; border-radius: 8px;
}}
QLabel#statNumOk {{ font-size: 24px; font-weight: 600; color: {t["success"]}; }}
QLabel#statNumFail {{ font-size: 24px; font-weight: 600; color: {t["danger"]}; }}
QLabel#statNumErr {{ font-size: 24px; font-weight: 600; color: {t["warn"]}; }}
QLabel#statNumConflict {{ font-size: 24px; font-weight: 600; color: {t["secondary"]}; }}
QLabel#statNumSkip {{ font-size: 24px; font-weight: 600; color: {t["tertiary"]}; }}
QLabel#statLabel {{ font-size: 12px; color: {t["secondary"]}; }}

QFrame#resultBox {{ background: {t["cardAlt"]}; border: 1px solid {t["border"]}; border-radius: 6px; }}
QLabel#resultTitle {{ font-size: 14px; font-weight: 600; color: {t["text"]}; }}
QLabel#rowName {{ font-size: 13px; font-weight: 600; color: {t["text"]}; }}
QLabel#rowMeta {{ font-size: 12px; color: {t["secondary"]}; }}
QLabel#dotOk {{ color: {t["success"]}; }}
QLabel#dotFail {{ color: {t["danger"]}; }}
QLabel#dotErr {{ color: {t["warn"]}; }}
QLabel#dotSkip {{ color: {t["tertiary"]}; }}

QWidget#statusBar {{
    background: {t["cardAlt"]}; border-top: 1px solid {t["border"]};
}}
QLabel#statusText {{ font-size: 12px; color: {t["secondary"]}; }}
QLabel#statusDotNormal, QLabel#statusDotOk, QLabel#statusDotWarn,
QLabel#statusDotError {{
    font-size: 10px;
}}
QLabel#statusDotNormal {{ color: {t["link"]}; }}
QLabel#statusDotOk {{ color: {t["success"]}; }}
QLabel#statusDotWarn {{ color: {t["warn"]}; }}
QLabel#statusDotError {{ color: {t["danger"]}; }}

QCheckBox {{ spacing: 7px; color: {t["secondary"]}; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {t["fieldBorder"]};
    border-radius: 4px; background: {t["field"]};
}}
QCheckBox::indicator:checked {{
    background: {t["accent"]}; border-color: {t["accent"]};
}}

QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {t["scroll"]}; border-radius: 4px; min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{ background: {t["scrollHover"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QMenu {{
    background: {t["card"]}; border: 1px solid {t["fieldBorder"]};
    border-radius: 6px; padding: 4px;
}}
QMenu::item {{ padding: 6px 22px; border-radius: 4px; color: {t["text"]}; }}
QMenu::item:selected {{ background: {t["activeBg"]}; }}

QDialog {{ background: {t["bg"]}; }}
QPlainTextEdit {{
    background: {t["card"]}; border: 1px solid {t["border"]};
    border-radius: 6px; padding: 8px; color: {t["text"]};
}}
QDialog QPushButton {{
    border-radius: 6px; padding: 7px 14px; min-height: 20px;
    font-size: 13px;
}}
QDialog QPushButton#primary {{
    background: {t["accent"]}; color: {t["onAccent"]}; font-weight: 600;
    padding: 7px 18px; min-height: 22px;
}}
QDialog QPushButton#primary:hover {{ background: {t["accentHover"]}; }}
QDialog QPushButton#primary:disabled {{
    background: {t["scroll"]}; color: {t["tertiary"]};
}}
QDialog QPushButton#secondary {{
    background: {t["card"]}; color: {t["text"]};
    border: 1px solid {t["fieldBorder"]}; font-weight: 500;
}}
QDialog QPushButton#secondary:hover {{ background: {t["navHover"]}; }}
QDialog QPushButton#secondary:disabled {{
    color: {t["tertiary"]}; border-color: {t["border"]};
}}
"""


def system_uses_dark_theme() -> bool:
    """Read the Windows app theme setting (HKCU ... Personalize)."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return int(value) == 0
    except Exception:
        return False


def _read_cfg() -> dict:
    for path in (CONFIG_FILE, LEGACY_CONFIG_FILE):
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def _write_cfg(data: dict) -> None:
    try:
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        merged = _read_cfg()
        merged.update(data)
        CONFIG_FILE.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _resolve_tools(cfg: dict) -> tuple[dict, list[str]]:
    tools: dict = dict(cfg.get("v2") or {})
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    candidates = {
        "repak_exe": base_dir / "tools" / "repak" / "repak.exe",
        "dotnet_exe": base_dir / "tools" / "dotnet" / "dotnet.exe",
        "uasset_cli_dll": base_dir / "tools" / "uassetcli" / "UAssetCLI.dll",
    }
    for key, candidate in candidates.items():
        if not str(tools.get(key) or "").strip() and candidate.is_file():
            tools[key] = str(candidate)
    missing = [
        key
        for key in ("repak_exe", "dotnet_exe", "uasset_cli_dll")
        if not str(tools.get(key) or "").strip()
    ]
    return tools, missing


def _app_icon() -> QIcon:
    for base in _asset_roots():
        for icon in (base / "assets" / "icon.ico", base / "assets" / "logo.png"):
            if icon.is_file():
                return QIcon(str(icon))
    return QIcon()


def _logo_pixmap(size: int = 30) -> QPixmap:
    pix = QPixmap()
    for base in _asset_roots():
        logo = base / "assets" / "logo.png"
        if logo.is_file():
            pix.load(str(logo))
            break
    if pix.isNull():
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _asset_roots() -> list[Path]:
    roots: list[Path] = []
    if hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))
    roots.append(Path(sys.executable).resolve().parent)
    roots.append(Path(__file__).resolve().parent.parent)
    return roots


def _default_quarantine_dir() -> Path:
    """Quarantine lives next to the executable in release zips."""
    return app_root() / "quarantine"


def _mix_color(a: QColor, b: QColor, amount: float) -> QColor:
    amount = max(0.0, min(1.0, amount))
    return QColor(
        round(a.red() + (b.red() - a.red()) * amount),
        round(a.green() + (b.green() - a.green()) * amount),
        round(a.blue() + (b.blue() - a.blue()) * amount),
        round(a.alpha() + (b.alpha() - a.alpha()) * amount),
    )


class ToggleSwitch(QAbstractButton):
    """Windows 11 style switch with a smooth knob animation."""

    def __init__(self, dark: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(48, 26)
        self._dark = bool(dark)
        self._progress = 1.0 if self.isChecked() else 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_progress)
        self.toggled.connect(self._animate_to_state)

    def set_theme(self, dark: bool) -> None:
        self._dark = bool(dark)
        self.update()

    def _on_progress(self, value: object) -> None:
        self._progress = float(value)
        self.update()

    def _animate_to_state(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        t = THEME_DARK if self._dark else THEME_LIGHT
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        track_w = 42
        track_h = 22
        x = (self.width() - track_w) / 2
        y = (self.height() - track_h) / 2
        off = QColor(t["scroll"])
        on = QColor(t["accent"])
        painter.setBrush(_mix_color(off, on, self._progress))
        painter.drawRoundedRect(
            int(round(x)), int(round(y)), track_w, track_h, track_h / 2, track_h / 2
        )

        knob = 16
        inset = 3
        travel = track_w - inset * 2 - knob
        kx = x + inset + travel * self._progress
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(
            int(round(kx)), int(round(y + (track_h - knob) / 2)), knob, knob
        )


class SegmentedControl(QWidget):
    """Windows 11 style segmented picker with an animated indicator."""

    currentIndexChanged = Signal(int)

    def __init__(self, options: list[str], dark: bool = False) -> None:
        super().__init__()
        self._options = list(options)
        self._dark = bool(dark)
        self._index = 0
        self._progress = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        metrics = QFontMetrics(self.font())
        widths = [metrics.horizontalAdvance(text) + 30 for text in self._options]
        self._min_w = max(260, sum(widths) + 12)
        self.setMinimumWidth(self._min_w)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_progress)

    def set_theme(self, dark: bool) -> None:
        self._dark = bool(dark)
        self.update()

    def currentIndex(self) -> int:
        return self._index

    def setCurrentIndex(self, index: int, animate: bool = True) -> None:
        index = max(0, min(len(self._options) - 1, int(index)))
        if index == self._index:
            return
        self._index = index
        self.currentIndexChanged.emit(index)
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._progress)
            self._anim.setEndValue(float(index))
            self._anim.start()
        else:
            self._progress = float(index)
            self.update()

    def _on_progress(self, value: object) -> None:
        self._progress = float(value)
        self.update()

    def sizeHint(self):  # noqa: N802
        return QSize(self._min_w, 36)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self._options:
            return
        inner = self.width() - 6
        seg = inner / len(self._options)
        index = int((event.position().x() - 3) / seg)
        self.setCurrentIndex(index)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        t = THEME_DARK if self._dark else THEME_LIGHT
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        outer = QRectF(0, 0, self.width(), self.height())
        painter.setBrush(QColor(t["activeBg"]))
        painter.drawRoundedRect(outer, 8, 8)

        count = len(self._options)
        if count and self._progress >= 0:
            margin = 3
            inner_w = self.width() - margin * 2
            seg_w = inner_w / count
            pos = max(0.0, min(float(count - 1), self._progress))
            sel = QRectF(
                margin + seg_w * pos,
                margin,
                seg_w,
                self.height() - margin * 2,
            )
            painter.setBrush(QColor(t["card"]))
            painter.drawRoundedRect(sel, 6, 6)

        painter.setPen(Qt.NoPen)
        for i, text in enumerate(self._options):
            cell = QRectF(3 + seg_w * i, 0, seg_w, self.height())
            if i == self._index and abs(self._progress - i) < 0.05:
                painter.setPen(QColor(t["text"]))
            else:
                painter.setPen(QColor(t["secondary"]))
            painter.drawText(cell, Qt.AlignCenter, text)


class RunWorker(QObject):
    """Runs the one-click pipeline in a background QThread."""

    log_line = Signal(str)
    status_text = Signal(str)
    progress = Signal(int, int, str)
    item_result = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.config: AppConfig | None = None
        self.tools: dict = {}
        self.cancel_event = threading.Event()
        self.pre_static: dict | None = None
        self.pre_dependency: dict | None = None
        self.pre_plan: dict | None = None

    def run(self) -> None:
        from .pipeline.v2_gui import run_v2_gui

        config = self.config
        if config is None:
            self.failed.emit("内部错误：缺少测试配置。")
            return
        try:
            summary = run_v2_gui(
                config,
                self.tools,
                emit=self._emit,
                cancel_event=self.cancel_event,
                pre_static=self.pre_static,
                pre_dependency=self.pre_dependency,
                pre_plan=self.pre_plan,
            )
        except Exception as exc:  # noqa: BLE001 - user-facing
            get_logger().exception("V2 Qt runner failed")
            self.failed.emit(str(exc))
            return
        self.finished.emit(summary)

    def _emit(self, kind: str, data: object) -> None:
        if kind == "log":
            self.log_line.emit(str(data))
        elif kind == "status":
            self.status_text.emit(str(data))
        elif kind == "progress":
            done, total, name = data  # type: ignore[misc]
            self.progress.emit(int(done), int(total), str(name))
        elif kind == "result":
            self.item_result.emit(data)
        # "done" is intentionally ignored: RunWorker emits its own result.


class NexusWorker(QObject):
    """Runs Nexus connection checks / MD5 identification in the background."""

    status_text = Signal(str)
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.mode = "validate"  # "validate" | "identify"
        self.api_key = ""
        self.folder = ""
        self.local_mods: list[dict] = []
        self.cancel_event = threading.Event()

    def run(self) -> None:
        from .nexus.cache import Md5Cache
        from .nexus.client import (
            NexusAuthError,
            NexusNetworkError,
            NexusRateLimitError,
        )
        from .nexus.identify import identify_paks

        try:
            if self.mode == "validate":
                from .nexus.client import NexusClient

                info = NexusClient(self.api_key).validate()
                self.finished.emit(
                    {
                        "kind": "validate",
                        "name": str(info.get("name") or info.get("user_id") or ""),
                    }
                )
                return

            if self.mode == "requirements":
                from .nexus.requirements import build_dependency_report

                report = build_dependency_report(
                    self.api_key,
                    local_mods=self.local_mods or None,
                )
                payload = dict(report)
                payload["kind"] = "requirements"
                self.finished.emit(payload)
                return

            folder = Path(self.folder)
            paks = list_mod_paks(folder)
            payload: dict = {"kind": "identify", "total": len(paks), "results": []}
            if paks:

                def emit_progress(done: int, total: int, name: str) -> None:
                    self.progress.emit(int(done), int(total), str(name))

                items = identify_paks(
                    paks,
                    self.api_key,
                    cache=Md5Cache(),
                    emit=emit_progress,
                    cancel_event=self.cancel_event,
                )
                payload["results"] = [item.as_dict() for item in items]
                payload["canceled"] = self.cancel_event.is_set()
            self.finished.emit(payload)
        except Exception as exc:  # noqa: BLE001 - deliver a typed, user-safe error
            if isinstance(exc, NexusAuthError):
                error: dict = {"kind": "auth", "message": str(exc)}
            elif isinstance(exc, NexusNetworkError):
                error = {"kind": "network", "message": str(exc)}
            elif isinstance(exc, NexusRateLimitError):
                error = {"kind": "rate", "message": str(exc)}
            else:
                error = {"kind": "error", "message": str(exc)}
            self.failed.emit(error)


class CalibrationWorker(QObject):
    """Launches the game once and estimates stable/startup timing in background."""

    log_line = Signal(str)
    status_text = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.exe_path = ""
        self.extra_args = ""
        self.cancel_event = threading.Event()

    def run(self) -> None:
        from pathlib import Path

        from .calibrate import calibrate

        try:
            result = calibrate(
                Path(self.exe_path),
                self.extra_args or "-windowed -nosplash",
                startup_timeout=240,
                max_seconds=180,
                emit_log=lambda text: self.log_line.emit(str(text)),
                cancel_event=self.cancel_event,
            )
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 - user-facing message
            self.failed.emit(str(exc))


class DependencyWorker(QObject):
    """Runs the local asset-dependency scan only (no game launch)."""

    status_text = Signal(str)
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.folder = ""
        self.files: list[str] = []
        self.tools: dict = {}
        self.cancel_event = threading.Event()

    def run(self) -> None:
        from pathlib import Path

        from .static.analyzer import analyze_folder
        from .static.deps import scan_dependencies

        try:
            folder = Path(self.folder)
            if not folder.is_dir():
                raise RuntimeError("依赖分析需要一个有效的 Mod 文件夹。")
            repak_exe = str(self.tools.get("repak_exe") or "")
            dotnet_exe = str(self.tools.get("dotnet_exe") or "")
            uasset_cli = str(self.tools.get("uasset_cli_dll") or "")
            if not repak_exe or not dotnet_exe or not uasset_cli:
                raise RuntimeError(
                    "依赖分析需要工具组件（repak / UAssetCLI / .NET）。"
                )
            only_paks: list[Path] | None = None
            if self.files:
                only_paks = [
                    Path(path) for path in self.files if Path(path).is_file()
                ] or None

            def status(text: str) -> None:
                self.status_text.emit(str(text))

            status("正在体检 Mod：读取文件清单与冲突…")
            static = analyze_folder(
                folder,
                repak_exe=repak_exe,
                log=status,
                only_paks=only_paks,
                cancel_event=self.cancel_event,
            )
            status("正在分析 Mod 间资产依赖（逐个解析资产，可能需要几分钟）…")

            def dep_progress(done: int, total: int, name: str) -> None:
                self.progress.emit(int(done), int(total), str(name))

            dependency = scan_dependencies(
                folder,
                repak_exe=repak_exe,
                dotnet_exe=dotnet_exe,
                uasset_cli_dll=uasset_cli,
                engine=str(self.tools.get("engine") or "VER_UE5_4"),
                asset_limit=int(self.tools.get("asset_limit") or 0),
                workers=int(self.tools.get("workers") or 4),
                log=status,
                progress=dep_progress,
                only_paks=only_paks,
                cancel_event=self.cancel_event,
            )
            self.finished.emit(
                {
                    "kind": "dependency_analysis",
                    "folder": str(folder),
                    "static": static.as_dict(),
                    "dependency": dependency,
                }
            )
        except Exception as exc:  # noqa: BLE001 - user-facing message
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, lang: str = "en") -> None:
        super().__init__()
        self.language = lang if lang in ("zh", "en") else "zh"
        set_language(self.language)

        self.cfg_data = _read_cfg()
        self.theme_mode = str(self.cfg_data.get("theme_mode") or "system")
        self.dark = (
            system_uses_dark_theme()
            if self.theme_mode == "system"
            else self.theme_mode == "dark"
        )

        # ----- persisted user state -----
        self.folder_path = str(self.cfg_data.get("mod_folder") or "")
        raw_mod_files = self.cfg_data.get("mod_files")
        self.mod_files: list[Path] = []
        if isinstance(raw_mod_files, list):
            for raw in raw_mod_files:
                try:
                    candidate = Path(str(raw))
                except (TypeError, OSError):
                    continue
                if candidate.is_file() and candidate.suffix.lower() == ".pak":
                    self.mod_files.append(candidate)
        self.mod_files = sorted(set(self.mod_files), key=lambda p: str(p).casefold())
        self.game_root = str(self.cfg_data.get("game_root") or "")
        self.exe_path = str(self.cfg_data.get("exe_path") or "")
        self.mod_dir_path = str(self.cfg_data.get("mod_dir") or "")
        self.report_dir_path = str(
            self.cfg_data.get("report_dir") or default_reports_dir()
        )
        self.quarantine_dir = str(
            self.cfg_data.get("quarantine_dir") or _default_quarantine_dir()
        )
        self.nexus_key = str(self.cfg_data.get("nexus_api_key") or "")
        self.mode = str(self.cfg_data.get("mode") or "isolated")
        self.disposition = str(self.cfg_data.get("disposition") or "quarantine")
        self.stable = int(self.cfg_data.get("stable_seconds") or 35)
        self.startup = int(self.cfg_data.get("startup_timeout") or 120)
        self.menu_hold = int(self.cfg_data.get("menu_hold_seconds") or 6)
        self.extra_args = str(self.cfg_data.get("extra_args") or "-windowed -nosplash")
        self.backup_mods = bool(self.cfg_data.get("backup_mods", True))
        self.close_running = bool(self.cfg_data.get("close_running", True))
        self.warmup = bool(self.cfg_data.get("warmup", False))
        self.analyze_deps = bool(self.cfg_data.get("analyze_deps", True))

        # ----- run state -----
        self.running = False
        self.cancel_event = threading.Event()
        self.summary: dict | None = None
        self.result_items: list[dict] = []
        self.log_lines: list[str] = []
        self.last_status = ""
        self.last_status_kind = "normal"
        self._thread: object | None = None
        self._worker: RunWorker | None = None
        self.nexus_busy = False
        self.nexus_state_text = ""
        self.nexus_results: list[dict] = []
        self.nexus_report_path: Path | None = None
        self.nexus_dep_path: Path | None = None
        self.nexus_mapping: dict = {}
        self._nexus_thread: object | None = None
        self._nexus_worker: NexusWorker | None = None
        self.dep_busy = False
        self.dep_report_path: Path | None = None
        self._dep_thread: object | None = None
        self._dep_worker: DependencyWorker | None = None
        self.analysis_static: dict | None = None
        self.analysis_dependency: dict | None = None
        self.analysis_plan: dict | None = None
        self._pending_static: dict | None = None
        self._pending_dependency: dict | None = None
        self._pending_plan: dict | None = None
        self.auto_calibrate = bool(self.cfg_data.get("auto_calibrate", True))
        cal = self.cfg_data.get("calibration")
        self.calibration: dict = cal if isinstance(cal, dict) else {}
        self._pending_config: AppConfig | None = None
        self._pending_tools: dict = {}
        self._calibrate_then_test = False
        self._cal_thread: object | None = None
        self._cal_worker: CalibrationWorker | None = None
        self._exit_requested = False

        self.setWindowTitle(f"{APP_NAME} v{VERSION} - by {AUTHOR}")
        self.setWindowIcon(_app_icon())
        self.resize(1240, 860)
        self.setMinimumSize(960, 640)

        self._build()
        self._check_theme()
        self._auto_detect_quiet()
        self._refresh_folder_hint()

        self._theme_timer = QTimer(self)
        self._theme_timer.timeout.connect(self._check_theme)
        self._theme_timer.start(2500)

    # ------------------------------------------------------------------ UI
    def _clear_root(self) -> None:
        central = self.centralWidget()
        if central is not None:
            self.setCentralWidget(None)
            central.deleteLater()

    def _build(self) -> None:
        self._clear_root()
        root = QWidget()
        root.setObjectName("root")
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_nav())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page = QWidget()
        page.setObjectName("page")
        scroll.setWidget(page)
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(42, 34, 42, 40)
        page_lay.setSpacing(20)

        page_lay.addLayout(self._build_hero())
        page_lay.addWidget(self._build_mod_card())
        page_lay.addWidget(self._build_test_card())
        page_lay.addWidget(self._build_advanced_card())
        page_lay.addWidget(self._build_nexus_card())
        page_lay.addStretch()
        body.addWidget(scroll, 1)

        root_lay.addLayout(body, 1)
        root_lay.addWidget(self._build_status_bar())
        self.setCentralWidget(root)
        self.setStyleSheet(fluent_qss(self.dark))
        self._refresh_static_texts()
        QTimer.singleShot(0, self._fade_in)

    def _refresh_static_texts(self) -> None:
        self.status_label.setText(self.last_status or _t("ready_status"))

    def _build_nav(self) -> QWidget:
        nav = QWidget()
        nav.setObjectName("navPane")
        nav.setFixedWidth(210)
        lay = QVBoxLayout(nav)
        lay.setContentsMargins(14, 22, 14, 18)
        lay.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(9)
        logo = QLabel()
        logo.setPixmap(_logo_pixmap())
        logo.setFixedSize(30, 30)
        brand_row.addWidget(logo)
        brand = QLabel(SHORT_NAME)
        brand.setObjectName("navBrand")
        brand_row.addWidget(brand)
        brand_row.addStretch()
        lay.addLayout(brand_row)

        hint = QLabel(_t("slogan"))
        hint.setObjectName("navHint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addSpacing(18)

        self.nav_test = QPushButton(_t("one_click_test"))
        self.nav_test.setObjectName("navActive")
        self.nav_test.setCursor(Qt.PointingHandCursor)
        self.nav_test.clicked.connect(self._scroll_top)
        lay.addWidget(self.nav_test)

        for text, cb in (
            (_t("tutorial"), self._open_tutorial),
            (_t("open_report"), self._open_report_folder),
            (_t("open_quarantine"), self._open_quarantine),
            (_t("view_log"), self._open_log_dialog),
            (_t("open_backup"), self._open_backup_folder),
            (_t("restore_backup"), self._restore_backup),
            (_t("about"), self._open_about),
        ):
            btn = QPushButton(text)
            btn.setObjectName("navItem")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(cb)
            lay.addWidget(btn)

        lay.addStretch()
        lang_label = "English" if self.language == "zh" else "中文"
        lang_btn = QPushButton(lang_label)
        lang_btn.setObjectName("langBtn")
        lang_btn.setCursor(Qt.PointingHandCursor)
        lang_btn.clicked.connect(self._choose_language)
        lay.addWidget(lang_btn)

        ver = QLabel(f"v{VERSION}")
        ver.setObjectName("navHint")
        lay.addWidget(ver)
        return nav

    def _build_hero(self) -> QVBoxLayout:
        hero = QVBoxLayout()
        hero.setSpacing(5)
        title = QLabel(SHORT_NAME)
        title.setObjectName("heroTitle")
        hero.addWidget(title)
        sub = QLabel(_t("slogan_sub"))
        sub.setObjectName("heroSub")
        sub.setWordWrap(True)
        hero.addWidget(sub)
        return hero

    def _build_mod_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(8)

        title = QLabel(_t("mod_folder"))
        title.setObjectName("cardTitle")
        lay.addWidget(title)
        desc = QLabel(_t("mod_folder_desc"))
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.folder_edit = QLineEdit()
        self.folder_edit.setObjectName("pathEdit")
        self.folder_edit.setText(self.folder_path)
        self.folder_edit.setPlaceholderText(_t("mod_folder"))
        self.folder_edit.textChanged.connect(self._refresh_folder_hint)
        row.addWidget(self.folder_edit, 1)

        select_btn = QPushButton(_t("select_mod_button"))
        select_btn.setObjectName("secondary")
        select_btn.setCursor(Qt.PointingHandCursor)
        select_btn.setMenu(QMenu(select_btn))
        self.mod_select_btn = select_btn
        menu = select_btn.menu()
        assert menu is not None
        folder_action = menu.addAction(_t("select_mod_folder_action"))
        folder_action.triggered.connect(self._browse_mod_source)
        files_action = menu.addAction(_t("select_mod_files_action"))
        files_action.triggered.connect(self._pick_mod_files)
        row.addWidget(select_btn)

        detect = QPushButton(_t("auto_detect"))
        detect.setObjectName("secondary")
        detect.setCursor(Qt.PointingHandCursor)
        self.mod_detect_btn = detect
        detect.clicked.connect(self._auto_detect_interactive)
        row.addWidget(detect)
        lay.addLayout(row)

        self.installed_label = QLabel()
        self.installed_label.setObjectName("installedHint")
        self.installed_label.setVisible(False)
        lay.addWidget(self.installed_label)

        self.folder_hint = QLabel()
        self.folder_hint.setObjectName("hint")
        self.folder_hint.setWordWrap(True)
        lay.addWidget(self.folder_hint)
        return card

    def _build_test_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        title = QLabel(_t("one_click_test"))
        title.setObjectName("cardTitle")
        lay.addWidget(title)
        desc = QLabel(_t("one_click_desc"))
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        self.progress = QProgressBar()
        self.progress.setObjectName("prog")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        self.run_status = QLabel()
        self.run_status.setObjectName("hint")
        self.run_status.setWordWrap(True)
        self.run_status.setVisible(False)
        lay.addWidget(self.run_status)

        cta_row = QHBoxLayout()
        cta_row.setSpacing(10)
        self.cta = QPushButton(_t("begin_test"))
        self.cta.setObjectName("primary")
        self.cta.setCursor(Qt.PointingHandCursor)
        self.cta.clicked.connect(self._start_test)
        cta_row.addWidget(self.cta)
        self.dep_btn = QPushButton(_t("dep_analysis_button"))
        self.dep_btn.setObjectName("secondary")
        self.dep_btn.setCursor(Qt.PointingHandCursor)
        self.dep_btn.clicked.connect(self._start_dependency_analysis)
        cta_row.addWidget(self.dep_btn)
        self.stop_btn = QPushButton(_t("stop"))
        self.stop_btn.setObjectName("secondary")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self._request_stop)
        self.stop_btn.setVisible(False)
        cta_row.addWidget(self.stop_btn)
        cta_row.addStretch()
        lay.addLayout(cta_row)

        self.stats_widget = QWidget()
        self.stats_lay = QHBoxLayout(self.stats_widget)
        self.stats_lay.setContentsMargins(0, 0, 0, 0)
        self.stats_lay.setSpacing(12)
        self.stats_widget.setVisible(False)
        lay.addWidget(self.stats_widget)

        self.results_box = QFrame()
        self.results_box.setObjectName("resultBox")
        self.results_lay = QVBoxLayout(self.results_box)
        self.results_lay.setContentsMargins(16, 12, 16, 12)
        self.results_lay.setSpacing(6)
        self.results_box.setVisible(False)
        lay.addWidget(self.results_box)
        return card

    def _build_advanced_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(10)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(10)
        self.adv_btn = QPushButton(_t("show_advanced"))
        self.adv_btn.setObjectName("secondary")
        self.adv_btn.setCursor(Qt.PointingHandCursor)
        self.adv_btn.clicked.connect(self._toggle_advanced)
        toggle_row.addWidget(self.adv_btn)
        tip = QLabel(_t("advanced_tip"))
        tip.setObjectName("dim")
        tip.setWordWrap(True)
        toggle_row.addWidget(tip, 1)
        lay.addLayout(toggle_row)

        self.adv_panel = QWidget()
        self.adv_panel.setVisible(False)
        grid = QGridLayout(self.adv_panel)
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)

        def labelled(text: str, widget: QWidget) -> None:
            lab = QLabel(text)
            lab.setObjectName("hint")
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(lab, grid.rowCount(), 0)
            grid.addWidget(widget, grid.rowCount() - 1, 1)

        # 测试策略：Windows 11 分段选择器
        strategy_lab = QLabel(_t("test_strategy"))
        strategy_lab.setObjectName("hint")
        strategy_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(strategy_lab, grid.rowCount(), 0)
        self.strategy_seg = SegmentedControl(
            [_t("mode_isolated"), _t("mode_strict")], dark=self.dark
        )
        self.strategy_seg.setCurrentIndex(0 if self.mode != "strict" else 1, animate=False)
        seg_row = QHBoxLayout()
        seg_row.addWidget(self.strategy_seg)
        seg_row.addStretch()
        grid.addLayout(seg_row, grid.rowCount() - 1, 1)

        self.stable_spin = QSpinBox()
        self.stable_spin.setRange(5, 600)
        self.stable_spin.setValue(self.stable)
        labelled(_t("stable"), self.stable_spin)

        self.startup_spin = QSpinBox()
        self.startup_spin.setRange(20, 900)
        self.startup_spin.setValue(self.startup)
        labelled(_t("startup_timeout"), self.startup_spin)

        self.menu_spin = QSpinBox()
        self.menu_spin.setRange(1, 120)
        self.menu_spin.setValue(self.menu_hold)
        labelled(_t("menu_hold"), self.menu_spin)

        calib_row = QHBoxLayout()
        calib_row.setSpacing(8)
        calib_lab = QLabel(_t("auto_calibrate_label"))
        calib_lab.setObjectName("hint")
        calib_row.addWidget(calib_lab)
        calib_row.addStretch()
        self.auto_cal_switch = ToggleSwitch(dark=self.dark)
        self.auto_cal_switch.setChecked(self.auto_calibrate)
        calib_row.addWidget(self.auto_cal_switch)
        self.calib_btn = QPushButton(_t("calibrate_now"))
        self.calib_btn.setObjectName("secondary")
        self.calib_btn.setCursor(Qt.PointingHandCursor)
        self.calib_btn.clicked.connect(self._start_manual_calibration)
        calib_row.addWidget(self.calib_btn)
        grid.addLayout(calib_row, grid.rowCount(), 0, 1, 2)
        self.calib_info = QLabel()
        self.calib_info.setObjectName("dim")
        self.calib_info.setWordWrap(True)
        grid.addWidget(self.calib_info, grid.rowCount(), 0, 1, 2)
        self._refresh_calibration_hint()

        # 不可用 Mod 处理：Windows 11 分段选择
        disp_lab = QLabel(_t("unusable_handling"))
        disp_lab.setObjectName("hint")
        disp_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(disp_lab, grid.rowCount(), 0)
        self.disposition_seg = SegmentedControl(
            [
                _t("disp_short_quarantine"),
                _t("disp_short_disable"),
                _t("disp_short_delete"),
                _t("disp_short_record"),
            ],
            dark=self.dark,
        )
        index = DISPOSITIONS.index(self.disposition) if self.disposition in DISPOSITIONS else 0
        self.disposition_seg.setCurrentIndex(index, animate=False)
        disp_row = QHBoxLayout()
        disp_row.addWidget(self.disposition_seg)
        disp_row.addStretch()
        grid.addLayout(disp_row, grid.rowCount() - 1, 1)
        disp_help = QLabel(_t("disposition_help"))
        disp_help.setObjectName("dim")
        disp_help.setWordWrap(True)
        grid.addWidget(disp_help, grid.rowCount(), 0, 1, 2)

        self.extra_edit = QLineEdit()
        self.extra_edit.setObjectName("plainEdit")
        self.extra_edit.setText(self.extra_args)
        labelled(_t("extra_args"), self.extra_edit)

        def switch_row(text: str) -> ToggleSwitch:
            lab = QLabel(text)
            lab.setObjectName("hint")
            row = QHBoxLayout()
            row.addWidget(lab)
            row.addStretch()
            sw = ToggleSwitch(dark=self.dark)
            row.addWidget(sw)
            grid.addLayout(row, grid.rowCount(), 0, 1, 2)
            return sw

        self.close_switch = switch_row(_t("close_running"))
        self.close_switch.setChecked(self.close_running)
        self.backup_switch = switch_row(_t("backup_mods"))
        self.backup_switch.setChecked(self.backup_mods)
        self.warmup_switch = switch_row(_t("warmup"))
        self.warmup_switch.setChecked(self.warmup)
        self.deps_switch = switch_row(_t("analyze_deps_label"))
        self.deps_switch.setChecked(self.analyze_deps)
        deps_help = QLabel(_t("analyze_deps_help"))
        deps_help.setObjectName("dim")
        deps_help.setWordWrap(True)
        grid.addWidget(deps_help, grid.rowCount(), 0, 1, 2)

        # 隔离目录：默认 exe 旁，也可自定义
        q_lab = QLabel(_t("quarantine_dir_label"))
        q_lab.setObjectName("hint")
        q_lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        grid.addWidget(q_lab, grid.rowCount(), 0)
        q_row = QHBoxLayout()
        q_row.setSpacing(8)
        self.quarantine_edit = QLineEdit()
        self.quarantine_edit.setObjectName("plainEdit")
        self.quarantine_edit.setText(self.quarantine_dir)
        q_row.addWidget(self.quarantine_edit, 1)
        q_browse = QPushButton(_t("browse"))
        q_browse.setObjectName("secondary")
        q_browse.setCursor(Qt.PointingHandCursor)
        q_browse.clicked.connect(self._browse_quarantine_dir)
        q_row.addWidget(q_browse)
        grid.addLayout(q_row, grid.rowCount() - 1, 1)

        # 改动即时同步到内存，切换语言/主题时不会丢失
        self.strategy_seg.currentIndexChanged.connect(
            lambda idx: setattr(
                self, "mode", "strict" if idx == 1 else "isolated"
            )
        )
        self.stable_spin.valueChanged.connect(lambda v: setattr(self, "stable", int(v)))
        self.startup_spin.valueChanged.connect(
            lambda v: setattr(self, "startup", int(v))
        )
        self.menu_spin.valueChanged.connect(
            lambda v: setattr(self, "menu_hold", int(v))
        )
        self.disposition_seg.currentIndexChanged.connect(
            lambda idx: setattr(
                self, "disposition", DISPOSITIONS[max(0, min(len(DISPOSITIONS) - 1, idx))]
            )
        )
        self.extra_edit.textChanged.connect(
            lambda text: setattr(self, "extra_args", str(text).strip())
        )
        self.close_switch.toggled.connect(
            lambda checked: setattr(self, "close_running", bool(checked))
        )
        self.backup_switch.toggled.connect(
            lambda checked: setattr(self, "backup_mods", bool(checked))
        )
        self.warmup_switch.toggled.connect(
            lambda checked: setattr(self, "warmup", bool(checked))
        )
        self.deps_switch.toggled.connect(
            lambda checked: setattr(self, "analyze_deps", bool(checked))
        )
        self.auto_cal_switch.toggled.connect(
            lambda checked: setattr(self, "auto_calibrate", bool(checked))
        )
        self.quarantine_edit.textChanged.connect(
            lambda text: setattr(self, "quarantine_dir", str(text).strip())
        )

        # 游戏根目录（仅在 Steam 自动检测失败时需要）
        self.game_root_edit = QLineEdit()
        self.game_root_edit.setObjectName("plainEdit")
        self.game_root_edit.setText(self.game_root)
        self.game_root_edit.textChanged.connect(
            lambda text: setattr(self, "game_root", str(text).strip())
        )
        grid.addWidget(QLabel(_t("game_root")), grid.rowCount(), 0)
        root_row = QHBoxLayout()
        root_row.addWidget(self.game_root_edit, 1)
        browse_root = QPushButton(_t("browse"))
        browse_root.setObjectName("secondary")
        browse_root.clicked.connect(self._browse_game_root)
        root_row.addWidget(browse_root)
        grid.addLayout(root_row, grid.rowCount() - 1, 1)
        grid.setColumnStretch(1, 1)
        lay.addWidget(self.adv_panel)
        return card

    def _build_nexus_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(8)

        title = QLabel(_t("nexus_key_label"))
        title.setObjectName("cardTitle")
        lay.addWidget(title)
        desc = QLabel(_t("nexus_desc"))
        desc.setObjectName("hint")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.key_edit = QLineEdit()
        self.key_edit.setObjectName("plainEdit")
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("Personal API Key")
        self.key_edit.setText(self.nexus_key)
        row.addWidget(self.key_edit, 1)

        save = QPushButton(_t("save_nexus_key"))
        save.setObjectName("secondary")
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save_nexus_key)
        row.addWidget(save)

        how = QPushButton(_t("get_nexus_key"))
        how.setObjectName("linkBtn")
        how.setCursor(Qt.PointingHandCursor)
        how.clicked.connect(self._open_nexus_help)
        row.addWidget(how)
        lay.addLayout(row)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.nexus_check_btn = QPushButton(_t("nexus_check_conn"))
        self.nexus_check_btn.setObjectName("secondary")
        self.nexus_check_btn.setCursor(Qt.PointingHandCursor)
        self.nexus_check_btn.clicked.connect(self._check_nexus_connection)
        actions.addWidget(self.nexus_check_btn)

        self.nexus_identify_btn = QPushButton(_t("nexus_identify_btn"))
        self.nexus_identify_btn.setObjectName("secondary")
        self.nexus_identify_btn.setCursor(Qt.PointingHandCursor)
        self.nexus_identify_btn.clicked.connect(self._identify_current_folder)
        actions.addWidget(self.nexus_identify_btn)

        self.nexus_view_btn = QPushButton(_t("nexus_view_results"))
        self.nexus_view_btn.setObjectName("secondary")
        self.nexus_view_btn.setCursor(Qt.PointingHandCursor)
        self.nexus_view_btn.clicked.connect(self._show_nexus_results)
        self.nexus_view_btn.setVisible(False)
        actions.addWidget(self.nexus_view_btn)
        actions.addStretch()
        lay.addLayout(actions)

        self.nexus_state_label = QLabel()
        self.nexus_state_label.setObjectName("hint")
        self.nexus_state_label.setWordWrap(True)
        lay.addWidget(self.nexus_state_label)

        self.nexus_progress = QProgressBar()
        self.nexus_progress.setObjectName("prog")
        self.nexus_progress.setRange(0, 1)
        self.nexus_progress.setValue(0)
        self.nexus_progress.setVisible(False)
        lay.addWidget(self.nexus_progress)

        privacy = QLabel(_t("nexus_md5_privacy"))
        privacy.setObjectName("hint")
        privacy.setWordWrap(True)
        lay.addWidget(privacy)

        if self.nexus_state_text:
            self.nexus_state_label.setText(self.nexus_state_text)
        return card

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("statusBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(24, 6, 24, 6)
        lay.setSpacing(8)
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        lay.addWidget(self.status_dot)
        self.status_label = QLabel(_t("ready_status"))
        self.status_label.setObjectName("statusText")
        lay.addWidget(self.status_label, 1)
        self.theme_seg = SegmentedControl(
            [_t("theme_light_name"), _t("theme_dark_name"), _t("follow_system")],
            dark=self.dark,
        )
        self.theme_seg.setCurrentIndex(self._theme_index(self.theme_mode), animate=False)
        self.theme_seg.currentIndexChanged.connect(self._on_theme_picker)
        lay.addWidget(self.theme_seg)
        return bar

    # ----------------------------------------------------------------- utils
    def _scroll_top(self) -> None:
        central = self.centralWidget()
        if central is None:
            return
        # find the QScrollArea child
        scroll = central.findChild(QScrollArea)
        if scroll is not None:
            scroll.verticalScrollBar().setValue(0)

    def _set_status(self, text: str, kind: str = "normal") -> None:
        self.last_status = text
        self.last_status_kind = kind if kind in ("normal", "ok", "warn", "error") else "normal"
        if hasattr(self, "status_label") and self.status_label is not None:
            self.status_label.setText(text)
        if hasattr(self, "status_dot") and self.status_dot is not None:
            suffix = {
                "normal": "Normal",
                "ok": "Ok",
                "warn": "Warn",
                "error": "Error",
            }.get(self.last_status_kind, "Normal")
            self.status_dot.setObjectName(f"statusDot{suffix}")
            self.status_dot.style().unpolish(self.status_dot)
            self.status_dot.style().polish(self.status_dot)

    def _color(self, name: str) -> str:
        t = THEME_DARK if self.dark else THEME_LIGHT
        return t.get(name, t["text"])

    def _check_theme(self) -> None:
        if self.theme_mode != "system":
            return
        dark = system_uses_dark_theme()
        if dark != self.dark:
            self._apply_theme()

    @staticmethod
    def _theme_index(mode: str) -> int:
        return {"light": 0, "dark": 1, "system": 2}.get(mode, 2)

    @staticmethod
    def _theme_mode_at(index: int) -> str:
        return ("light", "dark", "system")[max(0, min(2, int(index)))]

    def _on_theme_picker(self, index: int) -> None:
        mode = self._theme_mode_at(index)
        if mode == self.theme_mode:
            return
        self.theme_mode = mode
        _write_cfg({"theme_mode": mode})
        self._apply_theme()

    def _apply_theme(self) -> None:
        if self.theme_mode == "system":
            dark = system_uses_dark_theme()
        else:
            dark = self.theme_mode == "dark"
        if dark == self.dark:
            return
        self.dark = dark
        self.setStyleSheet(fluent_qss(self.dark))
        self._refresh_static_texts()
        self._set_status(self.last_status, self.last_status_kind)
        for switch in self.findChildren(ToggleSwitch):
            switch.set_theme(self.dark)
        for seg in self.findChildren(SegmentedControl):
            seg.set_theme(self.dark)
        self._fade_in()

    # ------------------------------------------------------------ language
    def _choose_language(self) -> None:
        if self.running:
            return
        # 点击即切换，不再弹出选择菜单
        new_lang = "en" if self.language == "zh" else "zh"
        if new_lang == self.language:
            return
        self.language = new_lang
        set_language(new_lang)
        _write_cfg({"language": new_lang})
        self._build()
        self._refresh_folder_hint()
        self._sync_post_build_state()

    def _fade_in(self) -> None:
        """Windows-like content fade-in after a rebuild."""
        central = self.centralWidget()
        if central is None:
            return
        effect = QGraphicsOpacityEffect(central)
        central.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: central.setGraphicsEffect(None))
        self._fade_anim = anim
        anim.start()

    # ------------------------------------------------------------- config
    def _collect_advanced(self) -> None:
        self.mode = "strict" if self.strategy_seg.currentIndex() == 1 else "isolated"
        self.stable = int(self.stable_spin.value())
        self.startup = int(self.startup_spin.value())
        self.menu_hold = int(self.menu_spin.value())
        idx = self.disposition_seg.currentIndex()
        self.disposition = DISPOSITIONS[max(0, min(len(DISPOSITIONS) - 1, idx))]
        self.extra_args = self.extra_edit.text().strip()
        self.close_running = self.close_switch.isChecked()
        self.backup_mods = self.backup_switch.isChecked()
        self.warmup = self.warmup_switch.isChecked()
        self.game_root = self.game_root_edit.text().strip()
        self.quarantine_dir = (
            self.quarantine_edit.text().strip() or str(_default_quarantine_dir())
        )

    def _save_prefs(self, config: AppConfig) -> None:
        _write_cfg(
            {
                "mod_folder": str(config.mod_folder) if config.mod_folder else "",
                "mod_files": [str(p) for p in config.mod_files],
                "exclude_files": [],
                "game_root": str(config.game_root) if config.game_root else "",
                "exe_path": str(config.exe_path) if config.exe_path else "",
                "mod_dir": str(config.mod_dir) if config.mod_dir else "",
                "report_dir": str(config.report_dir) if config.report_dir else "",
                "quarantine_dir": self.quarantine_dir,
                "mode": config.mode,
                "stable_seconds": config.stable_seconds,
                "startup_timeout": config.startup_timeout,
                "menu_hold_seconds": config.menu_hold_seconds,
                "extra_args": config.extra_args,
                "close_running": config.close_running,
                "backup_mods": config.backup_mods,
                "warmup": config.warmup,
                "analyze_deps": self.analyze_deps,
                "disposition": config.disposition,
                "language": self.language,
            }
        )

    def _save_nexus_key(self) -> None:
        key = self.key_edit.text().strip()
        _write_cfg({"nexus_api_key": key})
        self.nexus_key = key
        self.nexus_results = []
        self.nexus_view_btn.setVisible(False)
        self.nexus_state_label.setText(_t("nexus_saved_hint"))
        self._check_nexus_connection()

    # ------------------------------------------------------------- nexus
    def _check_nexus_connection(self) -> None:
        if self.running or self.nexus_busy or self.dep_busy:
            return
        key = self.key_edit.text().strip() or self.nexus_key
        if not key:
            self._set_nexus_state(_t("nexus_need_key"))
            return
        self._set_nexus_state(_t("nexus_conn_testing"))
        self._start_nexus_worker("validate", key=key)

    def _identify_current_folder(self) -> None:
        if self.running or self.nexus_busy or self.dep_busy:
            return
        key = self.key_edit.text().strip() or self.nexus_key
        if not key:
            self._set_nexus_state(_t("nexus_need_key"))
            return
        folder_text = self.folder_edit.text().strip() or self.folder_path
        if not folder_text:
            self._set_nexus_state(_t("nexus_need_folder"))
            return
        folder = Path(folder_text)
        if not folder.is_dir():
            self._set_nexus_state(_t("nexus_need_folder"))
            return
        if not list_mod_paks(folder):
            self._set_nexus_state(_t("nexus_no_paks"))
            return
        self.nexus_view_btn.setVisible(False)
        self._set_nexus_state(_t("nexus_preparing"))
        self._start_nexus_worker("identify", key=key, folder=str(folder))

    def _start_nexus_worker(
        self,
        mode: str,
        key: str,
        folder: str = "",
        local_mods: list[dict] | None = None,
    ) -> None:
        self.nexus_busy = True
        self.cancel_event.clear()
        self._set_nexus_busy_ui(True)

        worker = NexusWorker()
        worker.mode = mode
        worker.api_key = key
        worker.folder = folder
        worker.local_mods = local_mods or []
        worker.cancel_event = self.cancel_event
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_nexus_progress)
        worker.finished.connect(self._on_nexus_finished)
        worker.failed.connect(self._on_nexus_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        self._nexus_thread = thread
        self._nexus_worker = worker
        thread.start()

    def _set_nexus_busy_ui(self, busy: bool) -> None:
        if not hasattr(self, "nexus_check_btn"):
            return
        if hasattr(self, "calib_btn"):
            self.calib_btn.setEnabled(not busy and not self.running)
        if hasattr(self, "mod_select_btn"):
            self.mod_select_btn.setEnabled(not busy and not self.running)
        if hasattr(self, "mod_detect_btn"):
            self.mod_detect_btn.setEnabled(not busy and not self.running)
        if hasattr(self, "dep_btn"):
            self.dep_btn.setEnabled(not busy and not self.running and not self.dep_busy)
        self.nexus_check_btn.setEnabled(not busy and not self.running)
        self.nexus_identify_btn.setEnabled(not busy and not self.running)
        self.key_edit.setEnabled(not busy)
        self.nexus_progress.setVisible(busy)
        if busy:
            self.nexus_progress.setRange(0, 1)
            self.nexus_progress.setValue(0)

    def _set_nexus_state(self, text: str) -> None:
        self.nexus_state_text = text
        if hasattr(self, "nexus_state_label"):
            self.nexus_state_label.setText(text)

    def _on_nexus_progress(self, done: int, total: int, name: str) -> None:
        if hasattr(self, "nexus_state_label"):
            self.nexus_state_label.setText(
                _t("nexus_identifying", done=int(done), total=int(total), name=str(name))
            )
        if hasattr(self, "nexus_progress"):
            self.nexus_progress.setVisible(True)
            self.nexus_progress.setRange(0, max(1, int(total)))
            self.nexus_progress.setValue(int(done))

    def _on_nexus_finished(self, payload: object) -> None:
        self.nexus_busy = False
        self._finish_nexus_thread_cleanup()
        self._set_nexus_busy_ui(False)
        data = payload if isinstance(payload, dict) else {}
        if data.get("kind") == "validate":
            name = str(data.get("name") or "")
            suffix = f"（{name}）" if name else ""
            self._set_nexus_state(_t("nexus_conn_ok", user=suffix))
            return
        if data.get("kind") == "requirements":
            rows = data.get("rows") if isinstance(data.get("rows"), list) else []
            rows = [row for row in rows if isinstance(row, dict)]
            confirmed = int(data.get("confirmed_count") or 0)
            issues = sum(
                1 for row in rows if row.get("status") in ("missing", "error", "dlc")
            )
            self.nexus_dep_path = self._save_nexus_dep_report(rows)
            self._set_nexus_state(
                _t("nexus_deps_done", confirmed=confirmed, issues=issues)
            )
            self._show_nexus_dependencies(rows)
            return
        results = data.get("results") if isinstance(data.get("results"), list) else []
        self.nexus_results = [item for item in results if isinstance(item, dict)]
        self.nexus_report_path = (
            self._save_nexus_report(self.nexus_results) if self.nexus_results else None
        )
        total = int(data.get("total") or 0)
        found = sum(
            1
            for item in self.nexus_results
            if item.get("status") in ("found", "cached")
        )
        unknown = sum(
            1 for item in self.nexus_results if item.get("status") == "unknown"
        )
        possible = sum(
            1 for item in self.nexus_results if item.get("status") == "candidate"
        )
        errors = sum(
            1 for item in self.nexus_results if item.get("status") == "error"
        )
        if data.get("canceled"):
            text = _t(
                "nexus_identify_canceled",
                done=len(self.nexus_results),
                total=total,
            )
        else:
            text = _t(
                "nexus_identify_done",
                found=found,
                possible=possible,
                unknown=unknown,
                error=errors,
            )
        self._set_nexus_state(text)
        self.nexus_view_btn.setVisible(bool(self.nexus_results))

    def _on_nexus_failed(self, payload: object) -> None:
        self.nexus_busy = False
        self._finish_nexus_thread_cleanup()
        self._set_nexus_busy_ui(False)
        data = (
            payload
            if isinstance(payload, dict)
            else {"kind": "error", "message": str(payload)}
        )
        kind = str(data.get("kind") or "error")
        message = str(data.get("message") or "")
        if kind == "auth":
            text = _t("nexus_conn_bad")
        elif kind == "network":
            text = _t("nexus_conn_network", msg=message)
        elif kind == "rate":
            text = _t("nexus_rate_limited")
        else:
            text = _t("nexus_conn_error", msg=message)
        self._set_nexus_state(text)

    def _finish_nexus_thread_cleanup(self) -> None:
        if isinstance(self._nexus_thread, QThread):
            thread = self._nexus_thread
            thread.quit()
            thread.wait(3000)
        self._nexus_thread = None
        self._nexus_worker = None

    def _save_nexus_report(self, results: list[dict]) -> Path | None:
        from datetime import datetime

        try:
            report_dir = default_reports_dir()
            report_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            json_path = report_dir / f"nexus_identification_{stamp}.json"
            json_path.write_text(
                json.dumps(
                    {"results": results},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            csv_path = report_dir / f"nexus_identification_{stamp}.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                import csv

                writer = csv.writer(handle)
                writer.writerow(
                    ["file", "status", "mod_id", "mod_name", "source_or_author", "url"]
                )
                for item in results:
                    writer.writerow(
                        [
                            str(item.get("pak_name") or ""),
                            str(item.get("status") or ""),
                            str(item.get("mod_id") or ""),
                            str(item.get("mod_name") or ""),
                            str(item.get("file_name") or ""),
                            str(item.get("mod_url") or ""),
                        ]
                    )
            return json_path
        except OSError:
            return None

    def _show_nexus_results(self) -> None:
        if not self.nexus_results:
            return
        from .nexus.mapping import load_user_mapping

        self.nexus_mapping = load_user_mapping()
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("nexus_results_title"))
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            dlg.resize(
                max(980, min(1380, int(geo.width() * 0.92))),
                max(600, min(780, int(geo.height() * 0.9))),
            )
        else:
            dlg.resize(1280, 720)
        dlg.setMinimumSize(920, 560)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        note = QLabel(_t("nexus_result_note"))
        note.setObjectName("hint")
        note.setWordWrap(True)
        lay.addWidget(note)

        headers = [
            _t("nexus_col_file"),
            _t("nexus_col_status"),
            _t("nexus_col_mod"),
            _t("nexus_col_version"),
            _t("nexus_col_nexus_file"),
            _t("nexus_col_link"),
        ]
        table = QTableWidget(len(self.nexus_results), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        status_texts = {
            "found": _t("nexus_status_found"),
            "cached": _t("nexus_status_cached"),
            "candidate": _t("nexus_status_candidate"),
            "unknown": _t("nexus_status_unknown"),
            "error": _t("nexus_status_error"),
            "confirmed": _t("nexus_status_confirmed"),
            "ignored": _t("nexus_status_ignored"),
        }
        for row, item_data in enumerate(self.nexus_results):
            status, mod_id, mod_name, mod_url, source = self._nexus_display_values(
                item_data
            )
            pak_path = str(item_data.get("pak") or "")
            pak_name = str(item_data.get("pak_name") or Path(pak_path).name)
            display = {
                "mod_id": mod_id,
                "mod_name": mod_name,
                "mod_url": mod_url,
            }
            values = [
                pak_name,
                status_texts.get(status, status),
                mod_name,
                str(item_data.get("version") or ""),
                source,
                mod_url,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value or "—")
                if col == 0:
                    cell.setData(Qt.UserRole + 1, item_data)
                if col == 2:
                    cell.setData(Qt.UserRole + 2, display)
                if col == 5:
                    cell.setData(Qt.UserRole, value)
                    cell.setForeground(QColor(self._color("link")))
                table.setItem(row, col, cell)
        if table.rowCount() > 0:
            table.selectRow(0)
        table.cellDoubleClicked.connect(
            lambda row, _col: self._open_nexus_row(table, int(row))
        )
        lay.addWidget(table)

        row_actions = QHBoxLayout()
        row_actions.setSpacing(10)
        open_btn = QPushButton(_t("nexus_open_page"))
        open_btn.setObjectName("secondary")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(lambda: self._open_selected_nexus(table))
        row_actions.addWidget(open_btn)

        confirm_btn = QPushButton(_t("nexus_confirm_this"))
        confirm_btn.setObjectName("primary")
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.clicked.connect(lambda: self._confirm_nexus_selected(table))
        row_actions.addWidget(confirm_btn)

        candidate_btn = QPushButton(_t("nexus_other_candidates"))
        candidate_btn.setObjectName("secondary")
        candidate_btn.setCursor(Qt.PointingHandCursor)
        candidate_btn.clicked.connect(lambda: self._choose_nexus_candidate(table))
        row_actions.addWidget(candidate_btn)

        ignore_btn = QPushButton(_t("nexus_mark_ignored"))
        ignore_btn.setObjectName("secondary")
        ignore_btn.setCursor(Qt.PointingHandCursor)
        ignore_btn.clicked.connect(lambda: self._ignore_nexus_selected(table))
        row_actions.addWidget(ignore_btn)

        deps_btn = QPushButton(_t("nexus_check_deps"))
        deps_btn.setObjectName("secondary")
        deps_btn.setCursor(Qt.PointingHandCursor)

        def _go_deps() -> None:
            dlg.accept()
            self._start_requirements_check()

        deps_btn.clicked.connect(_go_deps)
        row_actions.addWidget(deps_btn)

        if self.nexus_report_path is not None:
            report_btn = QPushButton(_t("open_report"))
            report_btn.setObjectName("secondary")
            report_btn.setCursor(Qt.PointingHandCursor)
            report_btn.clicked.connect(self._open_report_folder)
            row_actions.addWidget(report_btn)
        row_actions.addStretch()
        close_btn = QPushButton(_t("nexus_close"))
        close_btn.setObjectName("secondary")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dlg.accept)
        row_actions.addWidget(close_btn)
        lay.addLayout(row_actions)
        dlg.setStyleSheet(fluent_qss(self.dark))
        dlg.exec()

    def _open_selected_nexus(self, table: QTableWidget, url_col: int = 5) -> None:
        row = table.currentRow()
        if row < 0:
            if table.rowCount() > 0:
                table.selectRow(0)
                row = 0
            else:
                return
        self._open_nexus_row(table, row, url_col)

    def _open_nexus_row(self, table: QTableWidget, row: int, url_col: int = 5) -> None:
        if row < 0 or row >= table.rowCount():
            return
        item = table.item(row, url_col)
        if item is None:
            return
        url = str(item.data(Qt.UserRole) or "")
        if not url:
            url = item.text().strip()
        if url.startswith("http"):
            if not QDesktopServices.openUrl(QUrl(url)):
                try:
                    os.startfile(url)  # type: ignore[attr-defined]  # noqa: S606
                except OSError:
                    self._set_nexus_state(_t("nexus_open_failed"))

    # ------------------------------------------------- nexus confirmations
    def _nexus_display_values(self, item_data: dict) -> tuple[str, int | None, str, str, str]:
        status = str(item_data.get("status") or "error")
        md5 = str(item_data.get("md5") or "")
        entry = self.nexus_mapping.get(md5.strip().lower()) if md5 else None
        if isinstance(entry, dict) and entry.get("choice") == "confirmed":
            try:
                mod_id = int(entry.get("mod_id") or 0) or None
            except (TypeError, ValueError):
                mod_id = None
            return (
                "confirmed",
                mod_id,
                str(entry.get("mod_name") or ""),
                str(entry.get("mod_url") or ""),
                str(entry.get("author") or item_data.get("file_name") or ""),
            )
        if isinstance(entry, dict) and entry.get("choice") == "ignored":
            return "ignored", None, "", "", ""
        try:
            mod_id = int(item_data.get("mod_id") or 0) or None
        except (TypeError, ValueError):
            mod_id = None
        return (
            status,
            mod_id,
            str(item_data.get("mod_name") or ""),
            str(item_data.get("mod_url") or ""),
            str(item_data.get("file_name") or ""),
        )

    def _nexus_row_info(
        self, table: QTableWidget, row: int
    ) -> tuple[dict | None, dict | None]:
        if row < 0 or row >= table.rowCount():
            return None, None
        item_data = table.item(row, 0)
        item_display = table.item(row, 2)
        data = item_data.data(Qt.UserRole + 1) if item_data is not None else None
        display = item_display.data(Qt.UserRole + 2) if item_display is not None else None
        return (
            data if isinstance(data, dict) else None,
            display if isinstance(display, dict) else None,
        )

    def _refresh_nexus_row(
        self,
        table: QTableWidget,
        row: int,
        status: str,
        display: dict | None,
        source: str = "",
    ) -> None:
        display = display or {}
        status_map = {
            "found": _t("nexus_status_found"),
            "cached": _t("nexus_status_cached"),
            "candidate": _t("nexus_status_candidate"),
            "unknown": _t("nexus_status_unknown"),
            "error": _t("nexus_status_error"),
            "confirmed": _t("nexus_status_confirmed"),
            "ignored": _t("nexus_status_ignored"),
        }
        name = str(display.get("mod_name") or "")
        url = str(display.get("mod_url") or "")
        table.item(row, 1).setText(status_map.get(status, status))
        table.item(row, 2).setText(name or "—")
        table.item(row, 2).setData(Qt.UserRole + 2, display)
        table.item(row, 4).setText(source or "—")
        table.item(row, 5).setText(url or "—")
        table.item(row, 5).setData(Qt.UserRole, url)

    def _confirm_nexus_selected(self, table: QTableWidget) -> None:
        row = table.currentRow()
        if row < 0 and table.rowCount() > 0:
            table.selectRow(0)
            row = 0
        item_data, display = self._nexus_row_info(table, row)
        if item_data is None or not item_data.get("md5"):
            self._set_nexus_state(_t("nexus_need_md5"))
            return
        display = display or {}
        mod_id = display.get("mod_id")
        mod_name = str(display.get("mod_name") or "")
        mod_url = str(display.get("mod_url") or "")
        if not mod_id or not mod_url:
            self._choose_nexus_candidate(table)
            return
        from .nexus.mapping import confirm_md5, load_user_mapping

        source = str(item_data.get("file_name") or "")
        confirm_md5(
            str(item_data["md5"]),
            int(mod_id),
            mod_name,
            mod_url,
            pak_name=str(item_data.get("pak_name") or ""),
            author=source,
        )
        self.nexus_mapping = load_user_mapping()
        self._set_nexus_state(_t("nexus_confirm_saved", name=mod_name))
        self._refresh_nexus_row(
            table,
            row,
            "confirmed",
            {"mod_id": mod_id, "mod_name": mod_name, "mod_url": mod_url},
            source=source,
        )

    def _choose_nexus_candidate(self, table: QTableWidget) -> None:
        row = table.currentRow()
        if row < 0 and table.rowCount() > 0:
            table.selectRow(0)
            row = 0
        item_data, _ = self._nexus_row_info(table, row)
        if item_data is None or not item_data.get("md5"):
            self._set_nexus_state(_t("nexus_need_md5"))
            return
        candidates = item_data.get("candidates") or []
        candidates = [c for c in candidates if isinstance(c, dict)]
        if not candidates:
            QMessageBox.information(
                self, _t("nexus_other_candidates"), _t("nexus_no_candidates")
            )
            return
        pak_name = str(item_data.get("pak_name") or "")
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("nexus_candidates_title", file=pak_name))
        dlg.resize(760, 420)
        lay = QVBoxLayout(dlg)
        list_box = QListWidget()
        for candidate in candidates:
            label = "{} — {}".format(
                candidate.get("mod_name") or "",
                candidate.get("author") or "",
            ).strip(" —")
            list_item = QListWidgetItem(label or str(candidate.get("mod_id") or ""))
            list_item.setData(Qt.UserRole, candidate)
            list_box.addItem(list_item)
        if list_box.count() > 0:
            list_box.setCurrentRow(0)
        lay.addWidget(list_box)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        ok_btn = QPushButton(_t("nexus_choose_candidate"))
        ok_btn.setObjectName("primary")
        ok_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn = QPushButton(_t("nexus_close"))
        cancel_btn.setObjectName("secondary")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        actions.addStretch()
        actions.addWidget(cancel_btn)
        actions.addWidget(ok_btn)
        lay.addLayout(actions)

        def _accept() -> None:
            current = list_box.currentItem()
            if current is None:
                return
            candidate = current.data(Qt.UserRole)
            if not isinstance(candidate, dict):
                return
            from .nexus.mapping import confirm_md5, load_user_mapping

            confirm_md5(
                str(item_data["md5"]),
                candidate.get("mod_id"),
                candidate.get("mod_name") or "",
                candidate.get("mod_url") or "",
                pak_name=pak_name,
                author=str(candidate.get("author") or ""),
            )
            self.nexus_mapping = load_user_mapping()
            author = str(candidate.get("author") or "")
            display = {
                "mod_id": candidate.get("mod_id"),
                "mod_name": candidate.get("mod_name") or "",
                "mod_url": candidate.get("mod_url") or "",
            }
            self._set_nexus_state(
                _t("nexus_confirm_saved", name=display["mod_name"])
            )
            self._refresh_nexus_row(
                table, row, "confirmed", display, source=author
            )
            dlg.accept()

        ok_btn.clicked.connect(_accept)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.setStyleSheet(fluent_qss(self.dark))
        dlg.exec()

    def _ignore_nexus_selected(self, table: QTableWidget) -> None:
        row = table.currentRow()
        if row < 0 and table.rowCount() > 0:
            table.selectRow(0)
            row = 0
        item_data, _ = self._nexus_row_info(table, row)
        if item_data is None or not item_data.get("md5"):
            self._set_nexus_state(_t("nexus_need_md5"))
            return
        from .nexus.mapping import ignore_md5, load_user_mapping

        ignore_md5(str(item_data["md5"]))
        self.nexus_mapping = load_user_mapping()
        self._set_nexus_state(_t("nexus_ignored_saved"))
        self._refresh_nexus_row(
            table, row, "ignored", {"mod_id": None, "mod_name": "", "mod_url": ""}
        )

    def _start_requirements_check(self) -> None:
        if self.running or self.nexus_busy or self.dep_busy:
            return
        key = self.key_edit.text().strip() or self.nexus_key
        if not key:
            self._set_nexus_state(_t("nexus_need_key"))
            return
        from .nexus.mapping import load_user_mapping

        mapping = load_user_mapping()
        confirmed = [
            record
            for record in mapping.values()
            if isinstance(record, dict)
            and record.get("choice") == "confirmed"
            and record.get("mod_id")
        ]
        if not confirmed:
            QMessageBox.information(
                self, _t("nexus_check_deps"), _t("nexus_deps_no_confirmed")
            )
            return
        self._set_nexus_state(_t("nexus_deps_running"))
        self._start_nexus_worker(
            "requirements",
            key=key,
            local_mods=self.nexus_results or None,
        )

    def _save_nexus_dep_report(self, rows: list[dict]) -> Path | None:
        from datetime import datetime

        try:
            report_dir = default_reports_dir()
            report_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            json_path = report_dir / f"nexus_dependencies_{stamp}.json"
            json_path.write_text(
                json.dumps({"rows": rows}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            csv_path = report_dir / f"nexus_dependencies_{stamp}.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                import csv

                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "file",
                        "source_mod",
                        "status",
                        "requirement",
                        "kind",
                        "notes",
                        "url",
                    ]
                )
                for row in rows:
                    writer.writerow(
                        [
                            row.get("pak_name") or "",
                            row.get("mod_name") or "",
                            row.get("status") or "",
                            row.get("req_name") or "",
                            row.get("kind") or "",
                            row.get("notes") or "",
                            row.get("url") or "",
                        ]
                    )
            return json_path
        except OSError:
            return None

    def _show_nexus_dependencies(self, rows: list[dict]) -> None:
        if not rows:
            QMessageBox.information(
                self, _t("nexus_deps_title"), _t("nexus_deps_none")
            )
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("nexus_deps_title"))
        dlg.resize(1080, 520)
        lay = QVBoxLayout(dlg)
        missing_map: dict[tuple, dict] = {}
        for row in rows:
            if str(row.get("status") or "") != "missing":
                continue
            key = (
                str(row.get("req_id") or ""),
                str(row.get("req_name") or ""),
                str(row.get("url") or ""),
            )
            item = missing_map.get(key)
            if item is None:
                item = {
                    "req_name": str(row.get("req_name") or ""),
                    "url": str(row.get("url") or ""),
                    "required_by": [],
                }
                missing_map[key] = item
            source = str(row.get("mod_name") or row.get("pak_name") or "")
            if source and source not in item["required_by"]:
                item["required_by"].append(source)
        missing = sorted(
            missing_map.values(),
            key=lambda item: str(item["req_name"]).casefold(),
        )
        if missing:
            preview = missing[:8]
            names = "、".join(
                str(item.get("req_name") or item.get("url") or "?")
                for item in preview
            )
            if len(missing) > len(preview):
                names += "…"
            summary_text = _t(
                "nexus_deps_missing_summary",
                count=len(missing),
                names=names,
            )
        else:
            local_candidates = sum(
                1
                for row in rows
                if str(row.get("status") or "") == "local_candidate"
            )
            if local_candidates:
                summary_text = _t(
                    "nexus_deps_local_summary", count=local_candidates
                )
            else:
                summary_text = _t("nexus_deps_all_ok_summary")
        summary_label = QLabel(summary_text)
        summary_label.setObjectName("hint")
        summary_label.setWordWrap(True)
        lay.addWidget(summary_label)
        headers = [
            _t("nexus_col_file"),
            _t("nexus_col_own_mod"),
            _t("nexus_col_status"),
            _t("nexus_col_need"),
            _t("nexus_col_link"),
        ]
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        status_map = {
            "installed": _t("nexus_dep_installed"),
            "local_candidate": _t("nexus_dep_local_candidate"),
            "missing": _t("nexus_dep_missing"),
            "external": _t("nexus_dep_external"),
            "dlc": _t("nexus_dep_dlc"),
            "error": _t("nexus_dep_error"),
        }
        for row, data in enumerate(rows):
            status = str(data.get("status") or "error")
            values = [
                str(data.get("pak_name") or ""),
                str(data.get("mod_name") or ""),
                status_map.get(status, status),
                str(data.get("req_name") or ""),
                str(data.get("url") or ""),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value or "—")
                if col == 4:
                    cell.setData(Qt.UserRole, value)
                    cell.setForeground(QColor(self._color("link")))
                table.setItem(row, col, cell)
        if table.rowCount() > 0:
            table.selectRow(0)
        table.cellDoubleClicked.connect(
            lambda row, _col: self._open_nexus_row(table, int(row), 4)
        )
        lay.addWidget(table)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        open_btn = QPushButton(_t("nexus_open_req_page"))
        open_btn.setObjectName("secondary")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(lambda: self._open_selected_nexus(table, 4))
        actions.addWidget(open_btn)
        if self.nexus_dep_path is not None:
            report_btn = QPushButton(_t("open_report"))
            report_btn.setObjectName("secondary")
            report_btn.setCursor(Qt.PointingHandCursor)
            report_btn.clicked.connect(self._open_report_folder)
            actions.addWidget(report_btn)
        actions.addStretch()
        close_btn = QPushButton(_t("nexus_close"))
        close_btn.setObjectName("primary")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dlg.accept)
        actions.addWidget(close_btn)
        lay.addLayout(actions)
        dlg.setStyleSheet(fluent_qss(self.dark))
        dlg.exec()

    # --------------------------------------------------------------- paths
    def _browse_mod_source(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            _t("mod_folder"),
            self.folder_path
            or self.mod_dir_path
            or self.game_root
            or str(Path.home()),
        )
        if path:
            self.mod_files = []
            self.folder_path = path
            self.folder_edit.setText(path)
            self._refresh_folder_hint()
            self._persist_current_prefs()

    def _pick_mod_files(self) -> None:
        start = (
            self.mod_dir_path
            or self.game_root
            or str(Path.home())
        )
        raw_files, _ = QFileDialog.getOpenFileNames(
            self,
            _t("add_files"),
            start,
            "Pak files (*.pak);;All files (*.*)",
        )
        files = [
            Path(p)
            for p in raw_files
            if Path(p).is_file() and is_mod_pak(Path(p).name)
        ]
        if not files:
            return
        self.mod_files = sorted(files, key=lambda p: str(p).casefold())
        self.folder_path = ""
        self.folder_edit.clear()
        self._refresh_folder_hint()
        self._persist_current_prefs()

    def _browse_game_root(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, _t("game_root"), self.game_root or str(Path.home())
        )
        if path:
            self.game_root_edit.setText(path)
            self._persist_current_prefs()

    def _browse_quarantine_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            _t("quarantine_dir_label"),
            self.quarantine_edit.text() or str(Path.home()),
        )
        if path:
            self.quarantine_edit.setText(path)
            self._persist_current_prefs()

    def _auto_detect_quiet(self) -> None:
        info = self._detect()
        if info is None:
            return
        if not self.game_root:
            self.game_root = str(info.root)
        if not self.exe_path:
            self.exe_path = str(info.exe)
        if not self.mod_dir_path:
            detected = detect_mod_dir(info)
            if detected:
                self.mod_dir_path = str(detected)

    def _detect(self):
        try:
            preferred = Path(self.game_root) if self.game_root else None
            return detect_game(preferred)
        except Exception:
            return None

    def _auto_detect_interactive(self) -> None:
        info = self._detect()
        if info is None:
            QMessageBox.warning(
                self,
                _t("未检测到游戏"),
                _t("未能在常见 Steam 目录中找到《严阵以待》。请手动选择游戏根目录。"),
            )
            return
        self.game_root = str(info.root)
        self.exe_path = str(info.exe)
        self.mod_files = []
        detected = detect_mod_dir(info)
        if detected:
            self.mod_dir_path = str(detected)
            if list_mod_paks(detected):
                self.folder_path = str(detected)
                self.folder_edit.setText(self.folder_path)
        if hasattr(self, "game_root_edit"):
            self.game_root_edit.setText(self.game_root)
        self._refresh_folder_hint()
        self._persist_current_prefs()
        self._set_status(
            self._local(f"已检测到游戏：{info.root}", f"Game detected: {info.root}")
        )

    def _folder_is_installed(self) -> bool:
        if not self.folder_path:
            return False
        try:
            folder = Path(self.folder_path).resolve()
        except OSError:
            return False
        mod_dir = Path(self.mod_dir_path).resolve() if self.mod_dir_path else None
        return mod_dir is not None and folder == mod_dir

    def _refresh_folder_hint(self) -> None:
        if not hasattr(self, "folder_hint"):
            return
        self.folder_path = self.folder_edit.text().strip()
        folder = Path(self.folder_path) if self.folder_path else None
        paks: list[Path] = []
        if folder is not None and folder.is_dir():
            paks = list_mod_paks(folder)
        manual_files = [p for p in self.mod_files if p.is_file()]
        installed = self._folder_is_installed()
        if folder is not None and folder.is_dir() and not paks:
            self.folder_hint.setText(_t("no_mods_found"))
            self.installed_label.setVisible(False)
        elif folder is not None and folder.is_dir():
            self.folder_hint.setText(_t("detected_mods", n=len(paks)))
            self.installed_label.setVisible(installed)
            if installed:
                self.installed_label.setText(_t("installed_hint"))
        elif manual_files:
            self.folder_hint.setText(_t("manual_files_selected", n=len(manual_files)))
            self.installed_label.setVisible(False)
        else:
            self.folder_hint.setText(_t("mods_hint"))
            self.installed_label.setVisible(False)
        if self.running:
            return
        can_start = bool(paks or manual_files) and self._tools_ok()
        self.cta.setEnabled(can_start)
        if hasattr(self, "dep_btn"):
            self.dep_btn.setEnabled(can_start)

    def _tools_ok(self) -> bool:
        _, missing = _resolve_tools(_read_cfg())
        return not missing

    def _toggle_advanced(self) -> None:
        current_anim = getattr(self, "_adv_anim", None)
        if current_anim is not None and current_anim.state() == QPropertyAnimation.Running:
            current_anim.stop()
        expanding = not self.adv_panel.isVisible()
        max_size = 16777215  # QWIDGETSIZE_MAX
        if expanding:
            self.adv_panel.setVisible(True)
            self.adv_panel.setMaximumHeight(0)
            start = 0
            end = max(1, self.adv_panel.sizeHint().height())
        else:
            start = max(1, self.adv_panel.height())
            end = 0

        anim = QPropertyAnimation(self.adv_panel, b"maximumHeight", self)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(start)
        anim.setEndValue(end)

        def _finish() -> None:
            if expanding:
                self.adv_panel.setMaximumHeight(max_size)
            else:
                self.adv_panel.setVisible(False)
                self.adv_panel.setMaximumHeight(max_size)

        anim.finished.connect(_finish)
        self._adv_anim = anim
        anim.start()
        self.adv_btn.setText(_t("hide_advanced") if expanding else _t("show_advanced"))

    # --------------------------------------------------------------- run
    def _build_config(self) -> AppConfig | None:
        self._collect_advanced()
        folder = Path(self.folder_path) if self.folder_path else None
        manual_files = [p for p in self.mod_files if p.is_file()]
        installed = False
        source = "folder"
        mod_folder: Path | None = None
        if folder is not None and folder.is_dir():
            manual_files = []
            installed = self._folder_is_installed()
            if installed:
                source = "installed"
                mod_dir = folder
            else:
                source = "folder"
                mod_folder = folder
        elif manual_files:
            source = "folder"
            mod_folder = None
        else:
            return None
        if not installed:
            if self.mod_dir_path:
                mod_dir = Path(self.mod_dir_path)
            else:
                info = self._detect()
                mod_dir = detect_mod_dir(info) if info else None
            if mod_dir is None:
                QMessageBox.warning(
                    self,
                    _t("未检测到游戏"),
                    _t("未能在常见 Steam 目录中找到《严阵以待》。请手动选择游戏根目录。"),
                )
                return None
        report_dir = Path(self.report_dir_path) if self.report_dir_path else None
        game_root = Path(self.game_root) if self.game_root else None
        exe_path = Path(self.exe_path) if self.exe_path else None
        return AppConfig(
            mod_folder=mod_folder,
            mod_files=manual_files,
            mod_dir=mod_dir,
            game_root=game_root,
            exe_path=exe_path,
            report_dir=report_dir,
            quarantine_dir=Path(self.quarantine_dir)
            if self.quarantine_dir
            else None,
            source=source,
            mode=self.mode,
            stable_seconds=max(5, self.stable),
            startup_timeout=max(20, self.startup),
            menu_hold_seconds=max(1, self.menu_hold),
            close_running=self.close_running,
            backup_mods=self.backup_mods,
            backup_dir=Path(self.cfg_data.get("backup_dir"))
            if self.cfg_data.get("backup_dir")
            else None,
            backup_max_file_mb=int(self.cfg_data.get("backup_max_file_mb") or 1500),
            backup_max_total_mb=int(self.cfg_data.get("backup_max_total_mb") or 10000),
            warmup=self.warmup,
            extra_args=self.extra_args or "-windowed -nosplash",
        )

    def _start_test(self) -> None:
        if self.running or self.nexus_busy or self.dep_busy:
            return
        audit("v2_test_qt")
        config = self._build_config()
        if config is None:
            return
        cfg = _read_cfg()
        tools, missing = _resolve_tools(cfg)
        if missing:
            QMessageBox.warning(
                self, _t("one_click_test"), _t("tool_missing_msg")
            )
            return
        tools["analyze_deps"] = self.analyze_deps
        if config.disposition == "delete":
            answer = QMessageBox.warning(
                self,
                _t("确认删除"),
                _t("confirm_delete_text"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self._save_prefs(config)
        self._save_current_options()

        if self.auto_calibrate and self._calibration_needed(config):
            self._pending_config = config
            self._pending_tools = tools
            self._calibrate_then_test = True
            self._start_calibration_worker()
            return
        self._run_test(config, tools)

    def _run_test(
        self,
        config: AppConfig,
        tools: dict,
        pre_static: dict | None = None,
        pre_dependency: dict | None = None,
        pre_plan: dict | None = None,
    ) -> None:
        self.result_items = []
        self.summary = None
        self.running = True
        self.cancel_event.clear()
        self._set_running_ui(True)
        self._set_status(_t("test_started"), "warn")

        worker = RunWorker()
        worker.config = config
        worker.tools = tools
        worker.cancel_event = self.cancel_event
        worker.pre_static = pre_static
        worker.pre_dependency = pre_dependency
        worker.pre_plan = pre_plan
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log_line.connect(self._on_log)
        worker.status_text.connect(self._on_status)
        worker.progress.connect(self._on_progress)
        worker.item_result.connect(self._on_item_result)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    # ----------------------------------------------------------- calibration
    def _calibration_needed(self, config: AppConfig) -> bool:
        if not self.auto_calibrate:
            return False
        cal = self.calibration
        if not isinstance(cal, dict) or not cal:
            return True
        if str(cal.get("exe_path") or "") != str(config.exe_path or ""):
            return True
        if str(cal.get("extra_args") or "") != str(config.extra_args or ""):
            return True
        updated = str(cal.get("updated_at") or "")
        try:
            from datetime import datetime

            age = datetime.now() - datetime.fromisoformat(updated)
            if age.total_seconds() >= 7 * 24 * 3600:
                return True
        except ValueError:
            return True
        return False

    def _refresh_calibration_hint(self) -> None:
        if not hasattr(self, "calib_info"):
            return
        cal = self.calibration
        if not isinstance(cal, dict) or not cal:
            self.calib_info.setText(_t("calib_info_none"))
            return
        stamp = str(cal.get("updated_at") or "")
        if len(stamp) >= 16:
            stamp = stamp[:16].replace("T", " ")

        def _fmt(value: object) -> str:
            try:
                number = float(value or 0)
            except (TypeError, ValueError):
                return "—"
            return f"{number:.0f}" if number else "—"

        self.calib_info.setText(
            _t(
                "calib_info_ok",
                time=stamp,
                window=_fmt(cal.get("window_seconds")),
                idle=_fmt(cal.get("idle_seconds")),
            )
        )

    def _start_manual_calibration(self) -> None:
        if self.running or self.nexus_busy or self.dep_busy:
            return
        if not self.exe_path or not Path(self.exe_path).is_file():
            QMessageBox.warning(self, _t("auto_timing"), _t("calib_no_exe"))
            return
        self._pending_config = None
        self._pending_tools = {}
        self._calibrate_then_test = False
        self._start_calibration_worker()

    def _start_calibration_worker(self) -> None:
        config = self._pending_config
        if config is not None:
            exe = str(config.exe_path or "")
            args = str(config.extra_args or "")
        else:
            exe = self.exe_path
            args = self.extra_args
        if not exe or not Path(exe).is_file():
            QMessageBox.warning(self, _t("auto_timing"), _t("calib_no_exe"))
            self._pending_config = None
            self._calibrate_then_test = False
            return
        audit("auto_calibrate")
        self.running = True
        self.cancel_event.clear()
        self._set_running_ui(True)
        self.progress.setVisible(False)
        self.run_status.setText(_t("calib_starting"))
        self._set_status(_t("calib_starting"), "warn")

        worker = CalibrationWorker()
        worker.exe_path = exe
        worker.extra_args = args
        worker.cancel_event = self.cancel_event
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log_line.connect(self._on_log)
        worker.status_text.connect(self._on_status)
        worker.finished.connect(self._on_calibration_done)
        worker.failed.connect(self._on_calibration_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        self._cal_thread = thread
        self._cal_worker = worker
        thread.start()

    def _finish_calibration_cleanup(self) -> None:
        if isinstance(self._cal_thread, QThread):
            thread = self._cal_thread
            thread.quit()
            thread.wait(3000)
        self._cal_thread = None
        self._cal_worker = None

    def _on_calibration_done(self, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        self.running = False
        self._finish_calibration_cleanup()
        self._set_running_ui(False)

        pending = self._pending_config
        tools = self._pending_tools
        self._pending_config = None
        self._pending_tools = {}
        pending_static = self._pending_static
        pending_dependency = self._pending_dependency
        pending_plan = self._pending_plan
        self._pending_static = None
        self._pending_dependency = None
        self._pending_plan = None
        then_test = self._calibrate_then_test
        self._calibrate_then_test = False

        if self.cancel_event.is_set():
            self._set_status(_t("calib_canceled"), "warn")
            return

        window = data.get("window_seconds")
        idle = data.get("idle_seconds")
        suggested = max(5, int(float(data.get("suggested_stable") or 35)))
        try:
            window_f = float(window or 0)
        except (TypeError, ValueError):
            window_f = 0.0
        startup = min(900, max(60, int(window_f * 1.8) + 30, self.startup))
        self.stable = suggested
        self.startup = startup
        if hasattr(self, "stable_spin"):
            self.stable_spin.setValue(suggested)
        if hasattr(self, "startup_spin"):
            self.startup_spin.setValue(startup)

        from datetime import datetime

        exe = str(
            (pending.exe_path if pending is not None else None) or self.exe_path or ""
        )
        extra = str(
            (pending.extra_args if pending is not None else None)
            or self.extra_args
            or ""
        )
        self.calibration = {
            "exe_path": exe,
            "extra_args": extra,
            "window_seconds": data.get("window_seconds"),
            "idle_seconds": data.get("idle_seconds"),
            "stable_seconds": suggested,
            "startup_timeout": startup,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_cfg(
            {
                "auto_calibrate": self.auto_calibrate,
                "calibration": self.calibration,
            }
        )
        if pending is not None:
            pending.stable_seconds = suggested
            pending.startup_timeout = startup
            self._save_prefs(pending)
        self._refresh_calibration_hint()

        def _fmt_seconds(value: object) -> str:
            if value is None or value == "":
                return "—"
            try:
                return f"{float(value):.0f}s"
            except (TypeError, ValueError):
                return "—"

        self._set_status(
            _t("calib_done", window=_fmt_seconds(window), idle=_fmt_seconds(idle)),
            "normal",
        )
        if then_test and pending is not None and tools:
            if pending_plan is not None:
                self._run_test(
                    pending,
                    tools,
                    pending_static,
                    pending_dependency,
                    pending_plan,
                )
            else:
                self._run_test(pending, tools)

    def _on_calibration_failed(self, message: str) -> None:
        self.running = False
        self._finish_calibration_cleanup()
        self._set_running_ui(False)
        self._pending_config = None
        self._pending_tools = {}
        self._pending_static = None
        self._pending_dependency = None
        self._pending_plan = None
        self._calibrate_then_test = False
        self._set_status(_t("calib_failed", msg=str(message)), "error")

    def _save_current_options(self) -> None:
        # values already persisted through _save_prefs(config); keep for memory.
        self.folder_path = self.folder_edit.text().strip()
        self.report_dir_path = self.report_dir_path

    def _persist_current_prefs(self) -> None:
        """Save source/advanced settings immediately so choices survive restarts."""
        if hasattr(self, "strategy_seg"):
            self._collect_advanced()
        folder_text = self.folder_edit.text().strip() if hasattr(self, "folder_edit") else self.folder_path
        folder_text = folder_text if folder_text and Path(folder_text).is_dir() else ""
        _write_cfg(
            {
                "mod_folder": folder_text,
                "mod_files": [str(p) for p in self.mod_files if p.is_file()],
                "exclude_files": [],
                "game_root": self.game_root,
                "exe_path": self.exe_path,
                "mod_dir": self.mod_dir_path,
                "report_dir": self.report_dir_path,
                "quarantine_dir": self.quarantine_dir,
                "mode": self.mode,
                "stable_seconds": self.stable,
                "startup_timeout": self.startup,
                "menu_hold_seconds": self.menu_hold,
                "extra_args": self.extra_args,
                "close_running": self.close_running,
                "backup_mods": self.backup_mods,
                "warmup": self.warmup,
                "analyze_deps": self.analyze_deps,
                "auto_calibrate": self.auto_calibrate,
                "disposition": self.disposition,
                "language": self.language,
            }
        )

    # ------------------------------------------------------- dependency only
    def _dependency_source_folder(self) -> Path | None:
        text = self.folder_edit.text().strip() or self.folder_path
        if text:
            folder = Path(text)
            if folder.is_dir():
                return folder
        if self.mod_files:
            parents = {str(p.parent.resolve()) for p in self.mod_files if p.is_file()}
            if len(parents) == 1:
                return Path(next(iter(parents)))
        if self.mod_dir_path:
            folder = Path(self.mod_dir_path)
            if folder.is_dir():
                return folder
        return None

    def _start_dependency_analysis(self) -> None:
        if self.running or self.nexus_busy or self.dep_busy:
            return
        folder = self._dependency_source_folder()
        if folder is None:
            QMessageBox.information(
                self, _t("dep_analysis_title"), _t("dep_need_folder")
            )
            return
        cfg = _read_cfg()
        tools, missing = _resolve_tools(cfg)
        if missing:
            QMessageBox.warning(
                self, _t("dep_analysis_title"), _t("tool_missing_msg")
            )
            return
        audit("dependency_analysis_only")
        self.dep_report_path = None
        self.cancel_event.clear()
        self._set_dep_busy_ui(True)

        worker = DependencyWorker()
        worker.folder = str(folder)
        if not self.folder_edit.text().strip() and self.mod_files:
            worker.files = [str(path) for path in self.mod_files if path.is_file()]
        worker.tools = tools
        worker.cancel_event = self.cancel_event
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status_text.connect(self._on_dep_status)
        worker.progress.connect(self._on_dep_progress)
        worker.finished.connect(self._on_dependency_done)
        worker.failed.connect(self._on_dependency_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        self._dep_thread = thread
        self._dep_worker = worker
        thread.start()

    def _start_test_from_analysis(self, dialog: QDialog | None = None) -> None:
        """Start one-click testing reusing the dependency analysis just completed."""
        if self.running or self.nexus_busy or self.dep_busy:
            return
        if not self.analysis_plan:
            return
        if dialog is not None:
            dialog.accept()
        audit("v2_test_qt_from_analysis")
        config = self._build_config()
        if config is None:
            QMessageBox.information(
                self, _t("one_click_test"), _t("dep_need_folder")
            )
            return
        cfg = _read_cfg()
        tools, missing = _resolve_tools(cfg)
        if missing:
            QMessageBox.warning(
                self, _t("one_click_test"), _t("tool_missing_msg")
            )
            return
        tools["analyze_deps"] = True
        if config.disposition == "delete":
            answer = QMessageBox.warning(
                self,
                _t("确认删除"),
                _t("confirm_delete_text"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self._save_prefs(config)
        self._save_current_options()

        if self.auto_calibrate and self._calibration_needed(config):
            self._pending_config = config
            self._pending_tools = tools
            self._pending_static = self.analysis_static
            self._pending_dependency = self.analysis_dependency
            self._pending_plan = self.analysis_plan
            self._calibrate_then_test = True
            self._start_calibration_worker()
            return
        self._run_test(
            config,
            tools,
            self.analysis_static,
            self.analysis_dependency,
            self.analysis_plan,
        )

    def _set_dep_busy_ui(self, busy: bool) -> None:
        self.dep_busy = busy
        self.cta.setEnabled(not busy and not self.running)
        if hasattr(self, "dep_btn"):
            self.dep_btn.setEnabled(
                not busy and not self.running and not self.nexus_busy
            )
        self.folder_edit.setEnabled(not busy)
        if hasattr(self, "mod_select_btn"):
            self.mod_select_btn.setEnabled(not busy and not self.running)
        if hasattr(self, "mod_detect_btn"):
            self.mod_detect_btn.setEnabled(not busy and not self.running)
        if hasattr(self, "adv_btn"):
            self.adv_btn.setEnabled(not busy)
        if hasattr(self, "nexus_check_btn"):
            enabled = not busy and not self.running and not self.nexus_busy
            self.nexus_check_btn.setEnabled(enabled)
            self.nexus_identify_btn.setEnabled(enabled)
            if hasattr(self, "key_edit"):
                self.key_edit.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.run_status.setVisible(busy)
        if busy:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.run_status.setText(_t("dep_analysis_started"))
            self._set_status(_t("dep_analysis_started"), "warn")

    def _on_dep_status(self, text: str) -> None:
        self.run_status.setVisible(True)
        self.run_status.setText(str(text))
        self._set_status(str(text), "warn")

    def _on_dep_progress(self, done: int, total: int, name: str) -> None:
        self.progress.setRange(0, max(1, int(total)))
        self.progress.setValue(int(done))
        text = _t("running_dots", done=int(done), total=int(total), name=str(name))
        self.run_status.setVisible(True)
        self.run_status.setText(text)
        self._set_status(text, "warn")

    def _finish_dep_cleanup(self) -> None:
        if isinstance(self._dep_thread, QThread):
            thread = self._dep_thread
            thread.quit()
            thread.wait(3000)
        self._dep_thread = None
        self._dep_worker = None

    def _on_dependency_done(self, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        self._finish_dep_cleanup()
        self._set_dep_busy_ui(False)
        static = data.get("static") if isinstance(data.get("static"), dict) else {}
        dependency = (
            data.get("dependency")
            if isinstance(data.get("dependency"), dict)
            else {}
        )
        self.dep_report_path = self._save_dependency_analysis_report(
            static, dependency
        )
        mods = len(dependency.get("paks") or [])
        edges = len(dependency.get("edges") or [])
        unresolved = len(dependency.get("unresolved_refs") or [])
        errors = len(dependency.get("parse_errors") or [])
        self._set_status(
            _t(
                "dep_analysis_done",
                mods=mods,
                edges=edges,
                unresolved=unresolved,
            ),
            "normal",
        )
        self._show_dependency_results(static, dependency)

    def _on_dependency_failed(self, message: str) -> None:
        self._finish_dep_cleanup()
        self._set_dep_busy_ui(False)
        self._set_status(_t("出错：") + str(message), "error")
        QMessageBox.critical(self, _t("dep_analysis_title"), str(message))

    def _save_dependency_analysis_report(
        self, static: dict, dependency: dict
    ) -> Path | None:
        from datetime import datetime

        try:
            report_dir = default_reports_dir()
            report_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            json_path = report_dir / f"dependency_analysis_{stamp}.json"
            json_path.write_text(
                json.dumps(
                    {
                        "static": static,
                        "dependency": dependency,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            csv_path = report_dir / f"dependency_analysis_{stamp}.csv"
            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                import csv

                writer = csv.writer(handle)
                writer.writerow(
                    ["from_mod", "to_mod", "asset_path", "confidence"]
                )
                for edge in dependency.get("edges") or []:
                    if not isinstance(edge, dict):
                        continue
                    writer.writerow(
                        [
                            edge.get("from_mod") or "",
                            edge.get("to_mod") or "",
                            edge.get("asset_path") or "",
                            edge.get("confidence") or "",
                        ]
                    )
            return json_path
        except OSError:
            return None

    def _show_dependency_results(self, static: dict, dependency: dict) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("dep_analysis_title"))
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            dlg.resize(
                max(980, min(1320, int(geo.width() * 0.9))),
                max(620, min(820, int(geo.height() * 0.88))),
            )
        else:
            dlg.resize(1200, 760)
        dlg.setMinimumSize(880, 560)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        edges = [e for e in dependency.get("edges") or [] if isinstance(e, dict)]
        unresolved = [
            u for u in dependency.get("unresolved_refs") or [] if isinstance(u, dict)
        ]
        errors = [e for e in dependency.get("parse_errors") or [] if isinstance(e, dict)]
        mods = len(dependency.get("paks") or [])
        summary = QLabel(
            _t(
                "dep_summary_line",
                mods=mods,
                edges=len(edges),
                unresolved=len(unresolved),
                errors=len(errors),
            )
        )
        summary.setObjectName("cardTitle")
        summary.setWordWrap(True)
        lay.addWidget(summary)

        def make_table(
            headers: list[str], rows: list[list[str]], stretch_cols: list[int]
        ) -> QTableWidget:
            table = QTableWidget(len(rows), len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.verticalHeader().setVisible(False)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeToContents
            )
            for col in stretch_cols:
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
            for row, values in enumerate(rows):
                for col, value in enumerate(values):
                    table.setItem(row, col, QTableWidgetItem(value or "—"))
            return table

        tabs = QTabWidget()
        edges_table = make_table(
            [
                _t("dep_col_source"),
                _t("dep_col_target"),
                _t("dep_col_asset"),
                _t("dep_col_confidence"),
            ],
            [
                [
                    str(edge.get("from_mod") or ""),
                    str(edge.get("to_mod") or ""),
                    str(edge.get("asset_path") or ""),
                    str(edge.get("confidence") or ""),
                ]
                for edge in edges
            ],
            [2],
        )
        tabs.addTab(edges_table, _t("dep_tab_edges"))

        unresolved_table = make_table(
            [
                _t("dep_col_source"),
                _t("dep_col_asset"),
                _t("dep_col_ref"),
            ],
            [
                [
                    str(item.get("mod") or ""),
                    str(item.get("asset") or ""),
                    str(item.get("ref") or ""),
                ]
                for item in unresolved
            ],
            [2],
        )
        tabs.addTab(unresolved_table, _t("dep_tab_unresolved"))

        errors_table = make_table(
            [
                _t("dep_col_source"),
                _t("dep_col_asset"),
                _t("dep_col_error"),
            ],
            [
                [
                    str(item.get("mod") or ""),
                    str(item.get("asset") or ""),
                    str(item.get("error") or ""),
                ]
                for item in errors
            ],
            [2],
        )
        tabs.addTab(errors_table, _t("dep_tab_errors"))

        try:
            from .planner.planner import build_plan

            plan = build_plan(static, dependency)
            groups = plan.as_dict().get("deploy_groups") or []
            self.analysis_static = static
            self.analysis_dependency = dependency
            self.analysis_plan = plan.as_dict()
        except Exception:  # noqa: BLE001 - preview is best-effort
            groups = []
            self.analysis_static = static
            self.analysis_dependency = dependency
            self.analysis_plan = None
        reason_map = {
            "isolated": _t("dep_reason_isolated"),
            "dependency": _t("dep_reason_dependency"),
            "strong_dependency": _t("dep_reason_strong_dependency"),
            "user_group": _t("dep_reason_user_group"),
        }
        groups_note = QLabel(_t("dep_group_preview_note"))
        groups_note.setObjectName("hint")
        groups_note.setWordWrap(True)
        groups_box = QWidget()
        groups_lay = QVBoxLayout(groups_box)
        groups_lay.setContentsMargins(0, 0, 0, 0)
        groups_lay.setSpacing(6)
        groups_lay.addWidget(groups_note)
        groups_table = make_table(
            [
                _t("dep_col_group"),
                _t("dep_col_reason"),
                _t("dep_col_files"),
                _t("dep_col_evidence"),
            ],
            [
                [
                    str(group.get("group_id") or ""),
                    reason_map.get(str(group.get("reason") or ""), str(group.get("reason") or "")),
                    ", ".join(str(name) for name in group.get("mods") or []),
                    "；".join(str(line) for line in group.get("evidence") or []),
                ]
                for group in groups
                if isinstance(group, dict)
            ],
            [2, 3],
        )
        groups_lay.addWidget(groups_table)
        tabs.addTab(groups_box, _t("dep_tab_groups"))
        lay.addWidget(tabs)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        if self.dep_report_path is not None:
            report_btn = QPushButton(_t("open_report"))
            report_btn.setObjectName("secondary")
            report_btn.setCursor(Qt.PointingHandCursor)
            report_btn.clicked.connect(self._open_report_folder)
            actions.addWidget(report_btn)
        actions.addStretch()
        if self.analysis_plan is not None:
            start_btn = QPushButton(_t("dep_start_test_button"))
            start_btn.setObjectName("primary")
            start_btn.setCursor(Qt.PointingHandCursor)
            start_btn.clicked.connect(
                lambda: self._start_test_from_analysis(dlg)
            )
            actions.addWidget(start_btn)
        close_btn = QPushButton(_t("nexus_close"))
        close_btn.setObjectName("secondary" if self.analysis_plan is not None else "primary")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(dlg.accept)
        actions.addWidget(close_btn)
        lay.addLayout(actions)
        dlg.setStyleSheet(fluent_qss(self.dark))
        dlg.exec()

    def _set_running_ui(self, running: bool) -> None:
        self.cta.setEnabled(not running)
        self.cta.setText(
            _t("stop")
            if running
            else (_t("rerun_test") if self.summary else _t("begin_test"))
        )
        self.stop_btn.setVisible(running)
        self.folder_edit.setEnabled(not running)
        if hasattr(self, "dep_btn"):
            self.dep_btn.setEnabled(
                not running and not self.nexus_busy and not self.dep_busy
            )
        if hasattr(self, "mod_select_btn"):
            self.mod_select_btn.setEnabled(not running and not self.nexus_busy)
        if hasattr(self, "mod_detect_btn"):
            self.mod_detect_btn.setEnabled(not running and not self.nexus_busy)
        self.progress.setVisible(running)
        self.run_status.setVisible(running)
        self.stats_widget.setVisible(False)
        self.results_box.setVisible(False)
        self.adv_btn.setEnabled(not running)
        if hasattr(self, "calib_btn"):
            self.calib_btn.setEnabled(not running and not self.nexus_busy)
        if hasattr(self, "nexus_check_btn"):
            enabled = not running and not self.nexus_busy
            self.nexus_check_btn.setEnabled(enabled)
            self.nexus_identify_btn.setEnabled(enabled)
        if running:
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
            self.run_status.setText(_t("running_now"))

    def _request_stop(self) -> None:
        if not self.running:
            return
        self.cancel_event.set()
        self._set_status(_t("stop_wait"), "warn")
        self.stop_btn.setEnabled(False)
        self.cta.setEnabled(False)

    def _on_log(self, text: str) -> None:
        self.log_lines.append(text)

    def _on_status(self, text: str) -> None:
        self.run_status.setVisible(True)
        self.run_status.setText(text)
        self._set_status(text, "warn")

    def _on_progress(self, done: int, total: int, name: str) -> None:
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(done)
        self.run_status.setVisible(True)
        self.run_status.setText(_t("running_dots", done=done, total=total, name=name))
        self._set_status(_t("running_dots", done=done, total=total, name=name), "warn")

    def _on_item_result(self, data: object) -> None:
        item = data
        if hasattr(item, "as_dict"):
            item = item.as_dict()
        if isinstance(item, dict):
            self.result_items.append(item)

    def _finish_thread_cleanup(self) -> None:
        if isinstance(self._thread, QThread):
            thread = self._thread
            thread.quit()
            thread.wait(3000)
        self._thread = None
        self._worker = None

    def _on_finished(self, summary: object) -> None:
        self.running = False
        self.summary = summary if isinstance(summary, dict) else {}
        self._finish_thread_cleanup()
        self._set_running_ui(False)
        self._show_results(self.summary)

    def _on_failed(self, message: str) -> None:
        self.running = False
        self._finish_thread_cleanup()
        self._set_running_ui(False)
        self._set_status(_t("出错：") + message, "error")
        QMessageBox.critical(self, _t("测试出错"), message)

    def _show_results(self, summary: dict) -> None:
        if not summary:
            self._set_status(_t("results_empty"))
            return
        self.progress.setValue(int(summary.get("total") or 0))
        self.stats_widget.setVisible(True)
        self._clear_stats()
        for key, obj in (
            ("Ok", "ok"),
            ("Fail", "fail"),
            ("Err", "error"),
            ("Conflict", "conflict"),
            ("Skip", "skipped"),
        ):
            self.stats_lay.addWidget(self._stat_tile(key, int(summary.get(obj) or 0)), 1)
        self.stats_lay.addStretch()

        results = list(summary.get("results") or [])
        bad = int(summary.get("fail") or 0) + int(summary.get("error") or 0) + int(
            summary.get("conflict") or 0
        )
        if bad == 0:
            ok_line = _t("summary_all_ok", n=len(results))
        else:
            ok_line = _t(
                "summary_counts",
                total=summary.get("total") or len(results),
                ok=summary.get("ok") or 0,
                fail=summary.get("fail") or 0,
                error=summary.get("error") or 0,
                conflict=summary.get("conflict") or 0,
                skipped=summary.get("skipped") or 0,
            )
        self._populate_result_rows(ok_line)
        self.cta.setText(_t("rerun_test"))
        self.cta.setEnabled(True)
        self._set_status(
            _t(
                "summary_counts",
                total=summary.get("total") or len(results),
                ok=summary.get("ok") or 0,
                fail=summary.get("fail") or 0,
                error=summary.get("error") or 0,
                conflict=summary.get("conflict") or 0,
                skipped=summary.get("skipped") or 0,
            ),
            "ok",
        )

    def _clear_stats(self) -> None:
        while self.stats_lay.count():
            item = self.stats_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _stat_tile(self, color_key: str, value: int) -> QWidget:
        tile = QFrame()
        tile.setObjectName("statTile")
        lay = QVBoxLayout(tile)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        num = QLabel(str(value))
        num.setObjectName(f"statNum{color_key}")
        num.setAlignment(Qt.AlignCenter)
        labels = {
            "Ok": "verdict_ok",
            "Fail": "verdict_fail",
            "Err": "verdict_error",
            "Conflict": "verdict_conflict",
            "Skip": "verdict_skipped",
        }
        lab = QLabel(_t(labels[color_key]))
        lab.setObjectName("statLabel")
        lab.setAlignment(Qt.AlignCenter)
        lay.addWidget(num)
        lay.addWidget(lab)
        return tile

    def _populate_result_rows(self, summary_line: str) -> None:
        while self.results_lay.count():
            item = self.results_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if not self.result_items:
            self.results_box.setVisible(False)
            return
        self.results_box.setVisible(True)
        title = QLabel(_t("summary_title"))
        title.setObjectName("resultTitle")
        self.results_lay.addWidget(title)
        note = QLabel(summary_line)
        note.setObjectName("hint")
        note.setWordWrap(True)
        self.results_lay.addWidget(note)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(230)
        list_widget = QWidget()
        list_lay = QVBoxLayout(list_widget)
        list_lay.setContentsMargins(0, 0, 0, 0)
        list_lay.setSpacing(4)
        for item in self.result_items:
            list_lay.addWidget(self._result_row(item))
        list_lay.addStretch()
        scroll.setWidget(list_widget)
        self.results_lay.addWidget(scroll)
        self._set_status("")

    def _result_row(self, item: dict) -> QWidget:
        verdict = str(item.get("verdict") or "")
        key = {
            "可用": "verdict_ok",
            "不可用": "verdict_fail",
            "错误": "verdict_error",
            "已存在": "verdict_conflict",
            "跳过": "verdict_skipped",
        }.get(verdict, "")
        dot = QLabel("●")
        dot.setObjectName(
            {
                "可用": "dotOk",
                "不可用": "dotFail",
                "错误": "dotErr",
                "已存在": "dotSkip",
                "跳过": "dotSkip",
            }.get(verdict, "dotSkip")
        )
        name = QLabel(str(item.get("filename") or ""))
        name.setObjectName("rowName")
        reason = str(item.get("reason") or "")
        elapsed = float(item.get("elapsed_seconds") or 0)
        meta = QLabel(f"{_t(key) if key else verdict} · {elapsed:.1f}s" + (f" · {reason}" if reason else ""))
        meta.setObjectName("rowMeta")
        meta.setWordWrap(True)
        lay = QHBoxLayout()
        lay.setSpacing(8)
        lay.addWidget(dot)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(name)
        col.addWidget(meta)
        lay.addLayout(col, 1)
        row = QWidget()
        row.setLayout(lay)
        return row

    # --------------------------------------------------------------- open
    def _open_report_folder(self) -> None:
        audit("open_report_qt")
        path: Path | None = None
        if self.dep_report_path is not None:
            dep_parent = Path(self.dep_report_path).parent
            if dep_parent.is_dir():
                path = dep_parent
        elif self.summary:
            for key in ("csv_path", "json_path", "v2_report"):
                if self.summary.get(key):
                    p = Path(str(self.summary[key]))
                    path = p.parent
                    break
        if path is None and self.report_dir_path:
            path = Path(self.report_dir_path)
        if path is None and self.folder_path:
            p = Path(self.folder_path)
            path = p.parent / (p.name + "_test_reports")
        if path is None or not path.is_dir():
            QMessageBox.information(self, _t("open_report"), _t("no_report"))
            return
        os.startfile(str(path))  # type: ignore[attr-defined]

    def _open_quarantine(self) -> None:
        path: Path | None = None
        if self.summary and self.summary.get("quarantine_dir"):
            p = Path(str(self.summary["quarantine_dir"]))
            if p.is_dir():
                path = p
        if path is None:
            candidates: list[Path] = []
            if self.quarantine_dir:
                candidates.append(Path(self.quarantine_dir))
            if self.folder_path:
                p = Path(self.folder_path)
                candidates.append(p.parent / (p.name + "_test_reports") / "quarantine")
            if self.game_root:
                candidates.append(
                    Path(self.game_root).parent / "RoN_ModCompat_Reports" / "quarantine"
                )
            if self.report_dir_path:
                candidates.append(Path(self.report_dir_path) / "quarantine")
            for candidate in candidates:
                if candidate.is_dir():
                    path = candidate
                    break
        if path is None or not path.is_dir():
            QMessageBox.information(
                self, _t("open_quarantine"), _t("open_quarantine_empty")
            )
            return
        os.startfile(str(path))  # type: ignore[attr-defined]

    def _find_backup_dir(self) -> Path | None:
        if self.summary and self.summary.get("backup_dir"):
            path = Path(str(self.summary["backup_dir"]))
            if path.is_dir():
                return path
        if self.cfg_data.get("backup_dir"):
            path = Path(str(self.cfg_data["backup_dir"]))
            if path.is_dir():
                return path
        default = default_backup_dir()
        return default if default.is_dir() else None

    def _open_backup_folder(self) -> None:
        backup_dir = self._find_backup_dir()
        if backup_dir is None or not backup_dir.is_dir():
            QMessageBox.information(
                self,
                _t("open_backup"),
                self._local(
                    "还没有备份目录。测试开始时会自动生成。",
                    "No backup folder yet. One is created automatically when a test starts.",
                ),
            )
            return
        os.startfile(str(backup_dir))  # type: ignore[attr-defined]

    def _local(self, zh: str, en: str) -> str:
        return en if self.language == "en" else zh

    def _restore_backup(self) -> None:
        audit("restore_backup_qt")
        backup_dir = self._find_backup_dir()
        if backup_dir is None or not (backup_dir / "manifest.json").is_file():
            QMessageBox.warning(
                self,
                self._local("未找到备份", "Backup not found"),
                self._local(
                    "还没有可用的备份清单。运行一次测试后会自动生成。",
                    "No backup manifest is available yet. Run a test to create one.",
                ),
            )
            return
        try:
            manifest = json.loads(
                (backup_dir / "manifest.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.critical(
                self, self._local("还原失败", "Restore failed"), str(exc)
            )
            return
        manifest_mod_dir = str(manifest.get("mod_dir") or "")
        created_at = str(manifest.get("created_at") or "")
        backup_enabled = bool(manifest.get("backup_enabled"))
        files = manifest.get("files")
        files = files if isinstance(files, dict) else {}
        mod_count = sum(
            1
            for name, meta in files.items()
            if isinstance(meta, dict)
            and not meta.get("dir")
            and (backup_dir / name).is_file()
        )
        recorded_dir = Path(manifest_mod_dir) if manifest_mod_dir else None
        if recorded_dir is not None and recorded_dir.is_dir():
            mod_dir = recorded_dir
        elif self.mod_dir_path:
            mod_dir = Path(self.mod_dir_path)
        else:
            info = self._detect()
            mod_dir = detect_mod_dir(info) if info is not None else None
        if mod_dir is None or not mod_dir.is_dir():
            QMessageBox.warning(
                self,
                self._local("未找到 Mod 目录", "Mod folder not found"),
                self._local(
                    "请先自动检测或选择 Mod 安装目录。",
                    "Run auto detect or choose the Mod install folder first.",
                ),
            )
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(self._local("确认还原", "Confirm restore"))
        dlg.resize(640, 360)
        lay = QVBoxLayout(dlg)
        detail_lines = [
            self._local("备份位置：", "Backup location: ") + str(backup_dir),
        ]
        if created_at:
            detail_lines.append(self._local("备份时间：", "Backup time: ") + created_at)
        detail_lines.append(
            self._local(
                f"备份内容：{mod_count} 个 .pak 文件",
                f"Backup contents: {mod_count} .pak file(s)",
            )
        )
        detail_lines.append(
            self._local("将还原到：", "Restore to: ") + str(mod_dir)
        )
        if recorded_dir is not None and recorded_dir != mod_dir:
            detail_lines.append(
                self._local(
                    f"注意：备份记录中的目录为 {recorded_dir}，与当前目标不同。",
                    f"Note: the backup was recorded for {recorded_dir}, which differs from the current target.",
                )
            )
        info = QLabel("\n".join(detail_lines))
        info.setWordWrap(True)
        lay.addWidget(info)
        if not backup_enabled or mod_count == 0:
            warn = QLabel(
                self._local(
                    "此备份没有保存任何 .pak 文件（测试时可能关闭了备份）。",
                    "This backup contains no .pak files (backups may have been disabled for that run).",
                )
            )
            warn.setObjectName("hint")
            warn.setWordWrap(True)
            lay.addWidget(warn)
        remove_new = QCheckBox(
            self._local(
                "完全还原（同时移除备份后新增的非系统 Mod）",
                "Full restore (also remove non-system mods added after the backup)",
            )
        )
        lay.addWidget(remove_new)
        open_dir = QPushButton(_t("open_backup"))
        open_dir.setObjectName("secondary")
        open_dir.setCursor(Qt.PointingHandCursor)
        open_dir.clicked.connect(
            lambda: os.startfile(str(backup_dir))  # type: ignore[attr-defined]
        )
        btns = QHBoxLayout()
        ok_btn = QPushButton(self._local("开始还原", "Restore now"))
        ok_btn.setObjectName("primary")
        cancel_btn = QPushButton(self._local("取消", "Cancel"))
        cancel_btn.setObjectName("secondary")
        btns.addWidget(open_dir)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        lay.addLayout(btns)
        dlg.setStyleSheet(fluent_qss(self.dark))

        result: dict = {}

        def _do_restore() -> None:
            dlg.accept()
            try:
                restored, removed = restore_backup(
                    backup_dir,
                    mod_dir,
                    remove_new=remove_new.isChecked(),
                )
            except (OSError, FileNotFoundError, json.JSONDecodeError) as exc:
                QMessageBox.critical(self, self._local("还原失败", "Restore failed"), str(exc))
                return
            result["restored"] = restored
            result["removed"] = removed
            msg = self._local(
                f"已还原 {len(restored)} 个文件。",
                f"Restored {len(restored)} file(s).",
            )
            if remove_new.isChecked():
                msg += self._local(
                    f"\n已移除新增文件 {len(removed)} 个。",
                    f"\nRemoved {len(removed)} new file(s).",
                )
            self.log_lines.append(self._local("还原备份：", "Restore backup: ") + msg)
            QMessageBox.information(self, self._local("还原完成", "Restore complete"), msg)

        ok_btn.clicked.connect(_do_restore)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def _open_nexus_help(self) -> None:
        QDesktopServices.openUrl(QUrl(NEXUS_KEY_URL))
        QMessageBox.information(
            self,
            "Nexus API Key",
            self._local(
                "打开页面后请滚动到最底部，在 Personal API Key 区域点 Generate/Create "
                "生成密钥并复制，然后粘贴到上方输入框并保存。",
                "After the page opens, scroll all the way to the bottom, "
                "use Generate/Create in the Personal API Key section, copy it, "
                "then paste it into the field above and save.",
            ),
        )

    def _open_log_dialog(self) -> None:
        lines = list(self.log_lines)
        if not lines:
            try:
                raw = Path(LOG_FILE).read_text(encoding="utf-8", errors="replace")
                lines = raw.splitlines()[-500:]
            except OSError:
                pass
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("view_log"))
        dlg.resize(760, 520)
        lay = QVBoxLayout(dlg)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n".join(lines) or _t("log_empty"))
        lay.addWidget(text)
        close = QPushButton(_t("stop"))
        close.setObjectName("secondary")
        close.clicked.connect(dlg.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        lay.addLayout(row)
        dlg.setStyleSheet(fluent_qss(self.dark))
        dlg.exec()

    def _open_tutorial(self) -> None:
        from .tutorial import TUTORIAL_TEXT, TUTORIAL_TEXT_EN

        dlg = QDialog(self)
        dlg.setWindowTitle(_t("tutorial"))
        dlg.resize(780, 640)
        lay = QVBoxLayout(dlg)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(TUTORIAL_TEXT_EN if self.language == "en" else TUTORIAL_TEXT)
        lay.addWidget(text)
        close = QPushButton(_t("stop"))
        close.setObjectName("secondary")
        close.clicked.connect(dlg.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close)
        lay.addLayout(row)
        dlg.setStyleSheet(fluent_qss(self.dark))
        dlg.exec()

    def _open_about(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("about"))
        dlg.resize(520, 380)
        lay = QVBoxLayout(dlg)
        info = QLabel(
            f"<h2>{SHORT_NAME} v{VERSION}</h2>"
            f"<p>{APP_NAME}</p>"
            f"<p>by {AUTHOR} · Ready or Not</p>"
            f"<p>{_t('about_contact')}: "
            f"<a href=\"mailto:{CONTACT_EMAIL}\">{CONTACT_EMAIL}</a></p>"
            f"<p>{_t('license_title')}</p>"
        )
        info.setWordWrap(True)
        info.setOpenExternalLinks(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        github = QPushButton(_t("open_github"))
        github.setObjectName("secondary")
        github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
        row.addWidget(github)
        license_btn = QPushButton(_t("license_title"))
        license_btn.setObjectName("secondary")
        license_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(RAW_LICENSE_URL))
        )
        row.addWidget(license_btn)
        row.addStretch()
        close = QPushButton(_t("stop"))
        close.setObjectName("primary")
        close.clicked.connect(dlg.accept)
        row.addWidget(close)
        lay.addLayout(row)
        dlg.setStyleSheet(fluent_qss(self.dark))
        dlg.exec()

    # ------------------------------------------------------------ lifecycle
    def closeEvent(self, event) -> None:  # noqa: N802
        if not self.running and not self.nexus_busy and not self.dep_busy:
            self._persist_current_prefs()
            event.accept()
            return
        if self._exit_requested:
            event.ignore()
            return
        answer = QMessageBox.question(
            self,
            _t("确认退出"),
            _t("任务正在进行，是否停止并退出？"),
        )
        if answer == QMessageBox.Yes:
            self._exit_requested = True
            self.cancel_event.set()
            self._set_status(_t("stop_wait"), "warn")
            self.stop_btn.setEnabled(False)
            self.hide()
            event.ignore()
            QTimer.singleShot(500, self._try_quit_after_cancel)
            QTimer.singleShot(10000, self._force_stop_stuck_tools)
        else:
            event.ignore()

    def _try_quit_after_cancel(self) -> None:
        if not self.running and not self.nexus_busy and not self.dep_busy:
            self.close()
        else:
            QTimer.singleShot(750, self._try_quit_after_cancel)

    def _force_stop_stuck_tools(self) -> None:
        """Kill only the analysis helper processes stuck under this app.

        This unblocks repak/UAssetCLI subprocess waits so the worker can finish
        its finally/cleanup. Game processes are not killed here; they are closed
        by the normal cancel path so Mod files are restored safely.
        """
        if not self._exit_requested:
            return
        if not (self.running or self.dep_busy):
            return
        try:
            import psutil
        except ImportError:
            return
        try:
            parent = psutil.Process(os.getpid())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return
        tool_names = {"repak.exe", "dotnet.exe", "uassetcli.exe"}
        for child in parent.children(recursive=True):
            try:
                name = (child.name() or "").lower()
                if name in tool_names and child.is_running():
                    child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def _sync_post_build_state(self) -> None:
        self._refresh_folder_hint()
        if self.running:
            self._set_running_ui(True)
        elif self.summary:
            self._show_results(self.summary)
        else:
            self._set_running_ui(False)
        if hasattr(self, "nexus_state_label"):
            self.nexus_state_label.setText(self.nexus_state_text)
        if hasattr(self, "nexus_view_btn"):
            self.nexus_view_btn.setVisible(bool(self.nexus_results))
        if hasattr(self, "nexus_check_btn"):
            self._set_nexus_busy_ui(self.nexus_busy)


def main() -> int:
    setup_logging()
    install_excepthook()
    get_logger().info("Qt GUI starting")
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:
        pass

    cfg = _read_cfg()
    lang = cfg.get("language") if cfg.get("language") in ("zh", "en") else "en"
    app = QApplication(sys.argv)
    app.setApplicationName(SHORT_NAME)
    app.setApplicationVersion(VERSION)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")
    app.setWindowIcon(_app_icon())

    window = MainWindow(lang=lang)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
