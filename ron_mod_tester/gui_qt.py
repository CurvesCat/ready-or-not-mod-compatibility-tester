"""RoNCT v0.3 modern GUI (PySide6, Windows 11 Fluent look).

Keeps the existing Python engine untouched; only replaces the outer shell.
Theme follows the Windows app theme automatically.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QVariantAnimation
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, SHORT_NAME, VERSION, AUTHOR, default_backup_dir
from .i18n import get_language, set_language, t as _t
from .locate import detect_game, detect_mod_dir
from .log import audit, get_logger, install_excepthook, setup_logging, LOG_FILE
from .models import AppConfig
from .safety import list_mod_paks, restore_backup

CONFIG_PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "RoNModCompatTester"
CONFIG_FILE = CONFIG_PATH / "config.json"
GITHUB_URL = "https://github.com/CurvesCat/ready-or-not-mod-compatibility-tester"
NEXUS_KEY_URL = "https://www.nexusmods.com/settings/api-keys"
RAW_LICENSE_URL = (
    "https://raw.githubusercontent.com/CurvesCat/"
    "ready-or-not-mod-compatibility-tester/main/LICENSE"
)

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
    "navHover": "#0000000D",
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
    "navHover": "#FFFFFF0D",
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
    font-family: "MiSans", "SF Pro Text", "SF Pro Display", "PingFang SC",
                 "Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI",
                 "Microsoft YaHei UI", "PingFang SC", sans-serif;
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
    border: none; border-radius: 4px; padding: 8px 16px; font-weight: 500;
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
    if not CONFIG_FILE.is_file():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
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


def load_bundled_fonts() -> bool:
    """Register bundled MiSans fonts (free to use, visually close to PingFang/SF)."""
    loaded = False
    for base in _asset_roots():
        fonts_dir = base / "assets" / "fonts"
        if not fonts_dir.is_dir():
            continue
        for font_file in sorted(fonts_dir.rglob("*.ttf")):
            try:
                if QFontDatabase.addApplicationFont(str(font_file)) >= 0:
                    loaded = True
            except Exception:
                continue
    return loaded


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


class MainWindow(QMainWindow):
    def __init__(self, lang: str = "zh") -> None:
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
        self.game_root = str(self.cfg_data.get("game_root") or "")
        self.exe_path = str(self.cfg_data.get("exe_path") or "")
        self.mod_dir_path = str(self.cfg_data.get("mod_dir") or "")
        self.report_dir_path = str(self.cfg_data.get("report_dir") or "")
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
            (_t("view_log"), self._open_log_dialog),
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

        ver = QLabel(f"v{VERSION} · preview")
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

        browse = QPushButton(_t("browse"))
        browse.setObjectName("secondary")
        browse.setCursor(Qt.PointingHandCursor)
        browse.clicked.connect(self._browse_folder)
        row.addWidget(browse)

        detect = QPushButton(_t("auto_detect"))
        detect.setObjectName("secondary")
        detect.setCursor(Qt.PointingHandCursor)
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

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.report_btn = QPushButton(_t("open_report"))
        self.report_btn.setObjectName("secondary")
        self.report_btn.setCursor(Qt.PointingHandCursor)
        self.report_btn.clicked.connect(self._open_report_folder)
        self.report_btn.setEnabled(False)
        action_row.addWidget(self.report_btn)

        self.quarantine_btn = QPushButton(_t("open_quarantine"))
        self.quarantine_btn.setObjectName("secondary")
        self.quarantine_btn.setCursor(Qt.PointingHandCursor)
        self.quarantine_btn.clicked.connect(self._open_quarantine)
        self.quarantine_btn.setEnabled(False)
        action_row.addWidget(self.quarantine_btn)
        action_row.addStretch()
        lay.addLayout(action_row)
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

        self.disposition_combo = QComboBox()
        for value in ("quarantine", "disable", "record"):
            label = {
                "quarantine": _t("disp_quarantine"),
                "disable": _t("disp_disable"),
                "record": _t("disp_record"),
            }[value]
            self.disposition_combo.addItem(label, value)
        index = self.disposition_combo.findData(self.disposition)
        self.disposition_combo.setCurrentIndex(max(0, index))
        labelled(_t("unusable_handling"), self.disposition_combo)

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
        self.disposition_combo.currentIndexChanged.connect(
            lambda _i: setattr(
                self,
                "disposition",
                str(self.disposition_combo.currentData() or "quarantine"),
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
        desc = QLabel(_t("app_desc"))
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
        self.disposition = str(self.disposition_combo.currentData() or "quarantine")
        self.extra_args = self.extra_edit.text().strip()
        self.close_running = self.close_switch.isChecked()
        self.backup_mods = self.backup_switch.isChecked()
        self.warmup = self.warmup_switch.isChecked()
        self.game_root = self.game_root_edit.text().strip()

    def _save_prefs(self, config: AppConfig) -> None:
        _write_cfg(
            {
                "mod_folder": str(config.mod_folder) if config.mod_folder else "",
                "game_root": str(config.game_root) if config.game_root else "",
                "exe_path": str(config.exe_path) if config.exe_path else "",
                "mod_dir": str(config.mod_dir) if config.mod_dir else "",
                "report_dir": str(config.report_dir) if config.report_dir else "",
                "mode": config.mode,
                "stable_seconds": config.stable_seconds,
                "startup_timeout": config.startup_timeout,
                "menu_hold_seconds": config.menu_hold_seconds,
                "extra_args": config.extra_args,
                "close_running": config.close_running,
                "backup_mods": config.backup_mods,
                "warmup": config.warmup,
                "disposition": config.disposition,
                "language": self.language,
            }
        )

    def _save_nexus_key(self) -> None:
        key = self.key_edit.text().strip()
        _write_cfg({"nexus_api_key": key})
        self.nexus_key = key
        QMessageBox.information(
            self, _t("one_click_test"), _t("nexus_key_saved")
        )

    # --------------------------------------------------------------- paths
    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, _t("mod_folder"), self.folder_path or str(Path.home())
        )
        if path:
            self.folder_path = path
            self.folder_edit.setText(path)
            self._refresh_folder_hint()

    def _browse_game_root(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, _t("game_root"), self.game_root or str(Path.home())
        )
        if path:
            self.game_root_edit.setText(path)

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
        if not self.folder_path and self.mod_dir_path:
            candidate = Path(self.mod_dir_path)
            if list_mod_paks(candidate):
                self.folder_path = self.mod_dir_path
                self.folder_edit.setText(self.folder_path)

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
        detected = detect_mod_dir(info)
        if detected:
            self.mod_dir_path = str(detected)
            if list_mod_paks(detected):
                self.folder_path = str(detected)
                self.folder_edit.setText(self.folder_path)
        if hasattr(self, "game_root_edit"):
            self.game_root_edit.setText(self.game_root)
        self._refresh_folder_hint()
        self._set_status(f"已检测到游戏：{info.root}")

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
        paks: list = []
        if folder is not None and folder.is_dir():
            paks = list_mod_paks(folder)
        installed = self._folder_is_installed()
        if folder is None or not folder.is_dir():
            self.folder_hint.setText(_t("mods_hint"))
            self.installed_label.setVisible(False)
        elif not paks:
            self.folder_hint.setText(_t("no_mods_found"))
            self.installed_label.setVisible(False)
        else:
            self.folder_hint.setText(_t("detected_mods", n=len(paks)))
            self.installed_label.setVisible(installed)
            if installed:
                self.installed_label.setText(_t("installed_hint"))
        if self.running:
            return
        can_start = bool(paks) and self._tools_ok()
        self.cta.setEnabled(can_start)

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
        if folder is None or not folder.is_dir():
            return None
        installed = self._folder_is_installed()
        if installed:
            source = "installed"
            mod_dir = folder
            mod_folder = None
        else:
            source = "folder"
            mod_folder = folder
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
            mod_dir=mod_dir,
            game_root=game_root,
            exe_path=exe_path,
            report_dir=report_dir,
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
        if self.running:
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
        self._save_prefs(config)
        self._save_current_options()

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

    def _save_current_options(self) -> None:
        # values already persisted through _save_prefs(config); keep for memory.
        self.folder_path = self.folder_edit.text().strip()
        self.report_dir_path = self.report_dir_path

    def _set_running_ui(self, running: bool) -> None:
        self.cta.setEnabled(not running)
        self.cta.setText(
            _t("stop")
            if running
            else (_t("rerun_test") if self.summary else _t("begin_test"))
        )
        self.stop_btn.setVisible(running)
        self.folder_edit.setEnabled(not running)
        self.progress.setVisible(running)
        self.run_status.setVisible(running)
        self.stats_widget.setVisible(False)
        self.results_box.setVisible(False)
        self.report_btn.setEnabled(False)
        self.quarantine_btn.setEnabled(False)
        self.adv_btn.setEnabled(not running)
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
        report_path = summary.get("csv_path") or summary.get("v2_report") or ""
        if report_path:
            self.report_btn.setEnabled(True)
            self.quarantine_btn.setEnabled(
                bool(summary.get("quarantine_dir"))
            )
        self.cta.setText(_t("rerun_test"))
        self.cta.setEnabled(True)
        self._set_status(
            "完成："
            f"可用 {summary.get('ok', 0)} / 不可用 {summary.get('fail', 0)} / "
            f"错误 {summary.get('error', 0)} / 已存在 {summary.get('conflict', 0)} / "
            f"跳过 {summary.get('skipped', 0)} · 共 {summary.get('total', 0)}",
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
        if self.summary:
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
        if not self.summary or not self.summary.get("quarantine_dir"):
            QMessageBox.information(
                self, _t("open_quarantine"), _t("results_empty")
            )
            return
        path = Path(str(self.summary["quarantine_dir"]))
        if not path.is_dir():
            QMessageBox.information(
                self, _t("open_quarantine"), _t("results_empty")
            )
            return
        os.startfile(str(path))  # type: ignore[attr-defined]

    def _local(self, zh: str, en: str) -> str:
        return en if self.language == "en" else zh

    def _restore_backup(self) -> None:
        audit("restore_backup_qt")
        backup_dir: Path | None = None
        if self.summary and self.summary.get("backup_dir"):
            backup_dir = Path(str(self.summary["backup_dir"]))
        elif self.cfg_data.get("backup_dir"):
            backup_dir = Path(str(self.cfg_data["backup_dir"]))
        if backup_dir is None:
            backup_dir = default_backup_dir()
        if not (backup_dir / "manifest.json").is_file():
            QMessageBox.warning(
                self,
                self._local("未找到备份", "Backup not found"),
                self._local(
                    f"未找到备份清单：{backup_dir}",
                    f"Backup manifest not found: {backup_dir}",
                ),
            )
            return
        mod_dir: Path | None = None
        if self.mod_dir_path:
            mod_dir = Path(self.mod_dir_path)
        if mod_dir is None or not mod_dir.is_dir():
            info = self._detect()
            if info is not None:
                mod_dir = detect_mod_dir(info)
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
        dlg.resize(560, 260)
        lay = QVBoxLayout(dlg)
        info = QLabel(
            self._local(
                f"将从：\n{backup_dir}\n\n还原非系统 .pak 文件到：\n{mod_dir}",
                f"Restore non-system .pak files from:\n{backup_dir}\n\nto:\n{mod_dir}",
            )
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        remove_new = QCheckBox(
            self._local(
                "完全还原（同时移除备份后新增的非系统 Mod）",
                "Full restore (also remove non-system mods added after the backup)",
            )
        )
        lay.addWidget(remove_new)
        btns = QHBoxLayout()
        ok_btn = QPushButton(self._local("开始还原", "Restore now"))
        ok_btn.setObjectName("primary")
        cancel_btn = QPushButton(self._local("取消", "Cancel"))
        cancel_btn.setObjectName("secondary")
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
            self.log_lines.append("还原备份：" + msg)
            QMessageBox.information(self, self._local("还原完成", "Restore complete"), msg)

        ok_btn.clicked.connect(_do_restore)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()

    def _open_nexus_help(self) -> None:
        QDesktopServices.openUrl(QUrl(NEXUS_KEY_URL))
        QMessageBox.information(
            self,
            "Nexus API Key",
            "登录 Nexus → Personal API Key → 生成/复制 → 粘贴到上方输入框并保存。",
        )

    def _open_log_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle(_t("view_log"))
        dlg.resize(760, 520)
        lay = QVBoxLayout(dlg)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n".join(self.log_lines) or _t("log_empty"))
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
            f"<p>{_t('license_title')}</p>"
        )
        info.setWordWrap(True)
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
        if not self.running:
            event.accept()
            return
        answer = QMessageBox.question(
            self,
            _t("确认退出"),
            _t("任务正在进行，是否停止并退出？"),
        )
        if answer == QMessageBox.Yes:
            self.cancel_event.set()
            self._set_status(_t("stop_wait"), "warn")
            self.stop_btn.setEnabled(False)
            event.ignore()
            QTimer.singleShot(1500, self._try_quit_after_cancel)
        else:
            event.ignore()

    def _try_quit_after_cancel(self) -> None:
        if not self.running:
            self.close()
        else:
            QTimer.singleShot(1500, self._try_quit_after_cancel)

    def _sync_post_build_state(self) -> None:
        self._refresh_folder_hint()
        if self.running:
            self._set_running_ui(True)
        elif self.summary:
            self._show_results(self.summary)
        else:
            self._set_running_ui(False)


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
    lang = cfg.get("language") if cfg.get("language") in ("zh", "en") else "zh"
    app = QApplication(sys.argv)
    app.setApplicationName(SHORT_NAME)
    app.setApplicationVersion(VERSION)
    load_bundled_fonts()
    app.setFont(QFont("MiSans", 10))
    app.setStyle("Fusion")
    app.setWindowIcon(_app_icon())

    window = MainWindow(lang=lang)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
