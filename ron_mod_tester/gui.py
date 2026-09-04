from __future__ import annotations

import json
import os
import queue
import sys
import threading
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    HORIZONTAL,
    LEFT,
    RIGHT,
    X,
    Y,
    BooleanVar,
    IntVar,
    StringVar,
    Tk,
    Toplevel,
    filedialog,
    messagebox,
    scrolledtext,
    ttk,
)

from . import APP_NAME, AUTHOR, VERSION, default_backup_dir
from .calibrate import calibrate
from .i18n import t, set_language, get_language
from .locate import detect_game, detect_mod_dir
from .models import AppConfig, TestResult
from .proc import find_game_processes, graceful_close
from .runner import TestRunner
from .safety import restore_backup
from .tutorial import TUTORIAL_TEXT, TUTORIAL_TEXT_EN


CONFIG_PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "RoNModCompatTester"
CONFIG_FILE = CONFIG_PATH / "config.json"

def _mode_labels() -> dict:
    return {"isolated": t("mode_isolated"), "strict": t("mode_strict")}


def _source_labels() -> dict:
    return {"folder": t("source_folder"), "installed": t("source_installed")}


def _disposition_labels() -> dict:
    return {
        "quarantine": t("disp_quarantine"),
        "disable": t("disp_disable"),
        "delete": t("disp_delete"),
        "record": t("disp_record"),
    }


def _key_for_label(table: dict, label: str, default: str) -> str:
    for key, value in table.items():
        if value == label:
            return key
    return default


class App:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title(f"{t('app_title')} v{VERSION} - by {AUTHOR}")
        root.geometry("1040x760")
        root.minsize(860, 620)

        self.var_mod_folder = StringVar()
        self.var_game_root = StringVar()
        self.var_exe = StringVar()
        self.var_mod_dir = StringVar()
        self.var_report_dir = StringVar()
        self.var_mode = StringVar(value="isolated")
        self.var_stable = IntVar(value=35)
        self.var_startup = IntVar(value=120)
        self.var_menu_hold = IntVar(value=6)
        self.var_extra_args = StringVar(value="-windowed -nosplash")
        self.var_warmup = BooleanVar(value=False)
        self.var_close_running = BooleanVar(value=True)
        self.var_backup = BooleanVar(value=True)
        self.var_backup_dir = StringVar(value="")
        self.var_backup_max_file = IntVar(value=1500)
        self.var_backup_max_total = IntVar(value=10000)
        self.var_source = StringVar(value="folder")
        self.var_disposition = StringVar(value="quarantine")
        self.mod_files: list[Path] = []
        self.exclude_files: list[Path] = []

        self.cancel_event = threading.Event()
        self.event_queue: queue.Queue[tuple] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.running = False
        self.calibrating = False
        self._close_when_done = False
        self.last_summary: dict | None = None
        self._row_index = 0

        self._build_ui()
        self._load_config()
        self._auto_detect(quiet=True)
        self.root.after(100, self._poll_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        if hasattr(self, "main"):
            self.main.destroy()
        pad = {"padx": 6, "pady": 4}

        main = ttk.Frame(self.root, padding=8)
        self.main = main
        main.pack(fill=BOTH, expand=True)

        top_bar = ttk.Frame(main)
        top_bar.pack(fill=X, pady=(0, 4))
        ttk.Label(
            top_bar,
            text=f"{t('app_title')} v{VERSION}",
            font=("Segoe UI", 13, "bold"),
        ).pack(side=LEFT)
        self.btn_language = ttk.Button(
            top_bar, text=t("language"), command=self._choose_language
        )
        self.btn_language.pack(side=LEFT, padx=(12, 0))
        self.btn_tutorial = ttk.Button(
            top_bar, text=t("tutorial"), command=self._open_tutorial
        )
        self.btn_tutorial.pack(side=RIGHT)
        ttk.Label(
            main,
            text=t("app_desc"),
            wraplength=1000,
            justify=LEFT,
        ).pack(anchor="w", pady=(0, 8))

        cfg = ttk.LabelFrame(main, text=t("path_config"), padding=6)
        cfg.pack(fill=X)
        cfg.columnconfigure(2, weight=1)

        self._path_row(cfg, 0, t("mod_folder"), self.var_mod_folder, self._browse_mod_folder)
        self._path_row(cfg, 1, t("game_root"), self.var_game_root, self._browse_game_root)
        ttk.Button(cfg, text=t("auto_detect"), command=self._auto_detect).grid(
            row=1, column=3, **pad
        )
        self._path_row(cfg, 2, t("exe_path"), self.var_exe, self._browse_exe)

        ttk.Label(cfg, text=t("mod_dir")).grid(row=3, column=0, sticky="e", **pad)
        self.mod_dir_combo = ttk.Combobox(cfg, textvariable=self.var_mod_dir)
        self.mod_dir_combo.grid(row=3, column=1, columnspan=2, sticky="ew", **pad)
        ttk.Button(cfg, text=t("browse"), command=self._browse_mod_dir).grid(
            row=3, column=3, **pad
        )

        self._path_row(cfg, 4, t("report_dir"), self.var_report_dir, self._browse_report_dir)

        ttk.Label(cfg, text=t("file_exclude")).grid(row=5, column=0, sticky="e", **pad)
        ttk.Button(cfg, text=t("add_files"), command=self._add_mod_files).grid(
            row=5, column=1, sticky="w", **pad
        )
        ttk.Button(cfg, text=t("exclude_files"), command=self._add_exclude_files).grid(
            row=5, column=2, sticky="w", **pad
        )
        self.selection_label = ttk.Label(cfg, text="", foreground="#666666")
        self.selection_label.grid(row=5, column=3, sticky="w", **pad)
        ttk.Button(cfg, text=t("clear_selection"), command=self._clear_selection).grid(
            row=6, column=1, sticky="w", **pad
        )
        self._update_selection_label()

        opt = ttk.LabelFrame(main, text=t("test_options"), padding=6)
        opt.pack(fill=X, pady=(8, 0))
        for col in range(6):
            opt.columnconfigure(col, weight=1)

        ttk.Label(opt, text=t("test_source")).grid(row=0, column=0, sticky="e", **pad)
        self.source_combo = ttk.Combobox(
            opt,
            textvariable=self.var_source,
            values=tuple(_source_labels().values()),
            state="readonly",
            width=16,
        )
        self.source_combo.grid(row=0, column=1, columnspan=2, sticky="w", **pad)

        ttk.Label(opt, text=t("test_strategy")).grid(row=0, column=3, sticky="e", **pad)
        self.mode_combo = ttk.Combobox(
            opt,
            textvariable=self.var_mode,
            values=tuple(_mode_labels().values()),
            state="readonly",
            width=18,
        )
        self.mode_combo.grid(row=0, column=4, columnspan=2, sticky="w", **pad)

        ttk.Label(opt, text=t("stable")).grid(row=1, column=0, sticky="e", **pad)
        ttk.Spinbox(
            opt, from_=5, to=300, textvariable=self.var_stable, width=6
        ).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(opt, text=t("startup_timeout")).grid(row=1, column=2, sticky="e", **pad)
        ttk.Spinbox(
            opt, from_=20, to=900, textvariable=self.var_startup, width=6
        ).grid(row=1, column=3, sticky="w", **pad)

        ttk.Label(opt, text=t("menu_hold")).grid(row=1, column=4, sticky="e", **pad)
        ttk.Spinbox(
            opt, from_=1, to=60, textvariable=self.var_menu_hold, width=6
        ).grid(row=1, column=5, sticky="w", **pad)

        ttk.Label(opt, text=t("extra_args")).grid(row=2, column=0, sticky="e", **pad)
        ttk.Entry(opt, textvariable=self.var_extra_args).grid(
            row=2, column=1, columnspan=5, sticky="ew", **pad
        )

        ttk.Label(opt, text=t("unusable_handling")).grid(row=3, column=0, sticky="e", **pad)
        self.disposition_combo = ttk.Combobox(
            opt,
            textvariable=self.var_disposition,
            values=tuple(_disposition_labels().values()),
            state="readonly",
            width=18,
        )
        self.disposition_combo.grid(row=3, column=1, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(
            opt, text=t("warmup"), variable=self.var_warmup
        ).grid(row=3, column=3, columnspan=3, sticky="w", **pad)

        ttk.Checkbutton(
            opt, text=t("close_running"), variable=self.var_close_running
        ).grid(row=4, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(
            opt, text=t("backup_mods"), variable=self.var_backup
        ).grid(row=4, column=3, columnspan=3, sticky="w", **pad)
        ttk.Button(opt, text=t("backup_settings"), command=self._open_backup_settings).grid(
            row=5, column=0, sticky="w", **pad
        )

        btns = ttk.Frame(main)
        btns.pack(fill=X, pady=8)
        self.btn_start = ttk.Button(btns, text=t("start_test"), command=self._start)
        self.btn_start.pack(side=LEFT)
        self.btn_stop = ttk.Button(
            btns, text=t("stop"), command=self._stop, state="disabled"
        )
        self.btn_stop.pack(side=LEFT, padx=(6, 0))
        self.btn_calibrate = ttk.Button(
            btns, text=t("auto_timing"), command=self._calibrate
        )
        self.btn_calibrate.pack(side=LEFT, padx=(6, 0))
        self.btn_report = ttk.Button(
            btns, text=t("open_report"), command=self._open_report, state="disabled"
        )
        self.btn_report.pack(side=LEFT, padx=(6, 0))
        self.btn_quarantine = ttk.Button(
            btns, text=t("open_quarantine"), command=self._open_quarantine, state="disabled"
        )
        self.btn_quarantine.pack(side=LEFT, padx=(6, 0))
        self.btn_restore = ttk.Button(
            btns, text=t("restore_backup"), command=self._restore_backup
        )
        self.btn_restore.pack(side=LEFT, padx=(6, 0))
        self.btn_backup_folder = ttk.Button(
            btns, text=t("open_backup"), command=self._open_backup_folder
        )
        self.btn_backup_folder.pack(side=LEFT, padx=(6, 0))

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill=X, pady=(0, 4))
        self.status_var = StringVar(value=t("ready_status"))
        ttk.Label(main, textvariable=self.status_var).pack(anchor="w")

        results_frame = ttk.LabelFrame(main, text=t("results"), padding=4)
        results_frame.pack(fill=BOTH, expand=True, pady=(8, 0))
        columns = ("index", "filename", "verdict", "elapsed", "reason")
        self.tree = ttk.Treeview(
            results_frame, columns=columns, show="headings", height=8
        )
        headings = {
            "index": t("col_index"),
            "filename": t("col_filename"),
            "verdict": t("col_verdict"),
            "elapsed": t("col_elapsed"),
            "reason": t("col_reason"),
        }
        widths = {"index": 50, "filename": 260, "verdict": 90, "elapsed": 80, "reason": 420}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w", stretch=col == "reason")
        tree_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        tree_scroll.pack(side=RIGHT, fill=Y)
        self.tree.tag_configure("ok", foreground="#1a7f37")
        self.tree.tag_configure("fail", foreground="#c62828")
        self.tree.tag_configure("warn", foreground="#b26a00")

        log_frame = ttk.LabelFrame(main, text=t("run_log"), padding=4)
        log_frame.pack(fill=BOTH, expand=True, pady=(8, 0))
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=8, state="disabled", wrap="word"
        )
        self.log_text.pack(fill=BOTH, expand=True)
        ttk.Label(main, text=f"{t('author')}: {AUTHOR}", foreground="#777777").pack(
            anchor="e", pady=(4, 0)
        )

    def _path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: StringVar,
        browse_cmd,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=6, pady=4
        )
        ttk.Button(parent, text=t("browse"), command=browse_cmd).grid(
            row=row, column=3, padx=6, pady=4
        )

    # -------------------------------------------------------------- actions
    def _browse_mod_folder(self) -> None:
        path = filedialog.askdirectory(title=t("选择包含 .pak Mod 文件的文件夹"))
        if path:
            self.var_mod_folder.set(path)
            if not self.var_report_dir.get().strip():
                self.var_report_dir.set(
                    str(Path(path).parent / (Path(path).name + "_test_reports"))
                )

    def _browse_game_root(self) -> None:
        path = filedialog.askdirectory(title=t("选择游戏根目录（包含 ReadyOrNot 文件夹）"))
        if path:
            self.var_game_root.set(path)
            self._auto_detect(quiet=True)

    def _browse_exe(self) -> None:
        path = filedialog.askopenfilename(
            title=t("选择游戏可执行文件"),
            filetypes=[(t("可执行文件"), "*.exe"), (t("所有文件"), "*.*")],
        )
        if path:
            self.var_exe.set(path)

    def _browse_mod_dir(self) -> None:
        path = filedialog.askdirectory(title=t("选择 Mod 安装目录（Paks 或 ~mods）"))
        if path:
            self.var_mod_dir.set(path)

    def _browse_report_dir(self) -> None:
        path = filedialog.askdirectory(title=t("选择报告输出目录"))
        if path:
            self.var_report_dir.set(path)

    def _add_mod_files(self) -> None:
        files = filedialog.askopenfilenames(
            title=t("选择要测试的 .pak 文件"),
            filetypes=[(t("Pak 文件"), "*.pak"), (t("所有文件"), "*.*")],
        )
        for path in files:
            p = Path(path)
            if p not in self.mod_files:
                self.mod_files.append(p)
        self._update_selection_label()

    def _add_exclude_files(self) -> None:
        files = filedialog.askopenfilenames(
            title=t("选择要排除的文件"),
            filetypes=[(t("Pak 文件"), "*.pak"), (t("所有文件"), "*.*")],
        )
        for path in files:
            p = Path(path)
            if p not in self.exclude_files:
                self.exclude_files.append(p)
        self._update_selection_label()

    def _clear_selection(self) -> None:
        self.mod_files.clear()
        self.exclude_files.clear()
        self._update_selection_label()

    def _update_selection_label(self) -> None:
        self.selection_label.configure(
            text=t(
                "selection_label",
                n=len(self.mod_files),
                m=len(self.exclude_files),
            )
        )

    def _auto_detect(self, quiet: bool = False) -> None:
        try:
            info = detect_game(Path(self.var_game_root.get()) if self.var_game_root.get() else None)
        except Exception as exc:  # pragma: no cover - defensive
            if not quiet:
                messagebox.showerror(t("自动检测失败"), str(exc))
            return
        if info is None:
            if not quiet:
                messagebox.showwarning(
                    t("未检测到游戏"),
                    t("未能在常见 Steam 目录中找到《严阵以待》。请手动选择游戏根目录。"),
                )
            return
        if not self.var_game_root.get().strip():
            self.var_game_root.set(str(info.root))
        if not self.var_exe.get().strip():
            self.var_exe.set(str(info.exe))
        values = [str(p) for p in info.mod_dir_candidates]
        self.mod_dir_combo["values"] = values
        if not self.var_mod_dir.get().strip():
            detected = detect_mod_dir(info)
            if detected:
                self.var_mod_dir.set(str(detected))

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert(END, text + "\n")
        self.log_text.see(END)
        self.log_text.configure(state="disabled")

    def _start(self) -> None:
        source = _key_for_label(_source_labels(), self.var_source.get(), "folder")
        disposition = _key_for_label(
            _disposition_labels(), self.var_disposition.get(), "quarantine"
        )
        mod_folder = self.var_mod_folder.get().strip()
        if source == "folder" and not mod_folder and not self.mod_files:
            messagebox.showwarning(
                t("缺少路径"), t("请先选择 Mod 文件夹，或手动添加至少一个 .pak 文件。")
            )
            return
        if disposition == "delete":
            if not messagebox.askyesno(
                t("确认删除"),
                t(
                    "你选择了“删除”不可用 Mod。\n\n"
                    "测试中判定为不可用的源文件会被永久删除，无法恢复。\n"
                    "确定继续吗？"
                ),
            ):
                return

        config = AppConfig(
            mod_folder=Path(mod_folder) if mod_folder else None,
            mod_files=list(self.mod_files),
            exclude_files=list(self.exclude_files),
            game_root=Path(self.var_game_root.get()) if self.var_game_root.get().strip() else None,
            exe_path=Path(self.var_exe.get()) if self.var_exe.get().strip() else None,
            mod_dir=Path(self.var_mod_dir.get()) if self.var_mod_dir.get().strip() else None,
            report_dir=Path(self.var_report_dir.get()) if self.var_report_dir.get().strip() else None,
            source=source,
            disposition=disposition,
            mode=_key_for_label(_mode_labels(), self.var_mode.get(), "isolated"),
            stable_seconds=max(5, int(self.var_stable.get())),
            startup_timeout=max(20, int(self.var_startup.get())),
            menu_hold_seconds=max(1, int(self.var_menu_hold.get())),
            close_running=bool(self.var_close_running.get()),
            backup_mods=bool(self.var_backup.get()),
            backup_dir=Path(self.var_backup_dir.get()) if self.var_backup_dir.get().strip() else None,
            backup_max_file_mb=max(100, int(self.var_backup_max_file.get())),
            backup_max_total_mb=max(100, int(self.var_backup_max_total.get())),
            warmup=bool(self.var_warmup.get()),
            extra_args=self.var_extra_args.get().strip(),
        )
        self._save_config(config)

        for item in self.tree.get_children():
            self.tree.delete(item)
        self._row_index = 0
        self.progress["value"] = 0
        self.progress["maximum"] = 1
        self.last_summary = None
        self.btn_report.configure(state="disabled")
        self.btn_quarantine.configure(state="disabled")

        self.running = True
        self.cancel_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_calibrate.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set(t("正在启动测试…"))
        self._append_log("===== 开始测试 =====")

        self.worker = threading.Thread(
            target=self._worker_main, args=(config,), daemon=False
        )
        self.worker.start()

    def _worker_main(self, config: AppConfig) -> None:
        runner = TestRunner(
            config=config,
            emit=lambda kind, data: self.event_queue.put((kind, data)),
            cancel_event=self.cancel_event,
        )
        try:
            runner.run()
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            self.event_queue.put(("error", str(exc)))

    def _stop(self) -> None:
        self.cancel_event.set()
        self.status_var.set(t("正在停止，请等待当前测试收尾…"))
        self.btn_stop.configure(state="disabled")

    def _calibrate(self) -> None:
        exe = self._resolve_exe_path()
        if exe is None or not exe.is_file():
            messagebox.showwarning(t("未找到游戏"), t("请先自动检测或手动选择游戏可执行文件。"))
            return
        if self.running or self.calibrating:
            return
        running = find_game_processes(exe)
        if running:
            if not messagebox.askyesno(
                t("游戏正在运行"),
                t("检测到游戏正在运行。自动测时需要关闭它再启动，是否关闭？"),
            ):
                return
            graceful_close(running, timeout=6)

        self.calibrating = True
        self.cancel_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_calibrate.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set(t("正在自动测时（会启动一次游戏）…"))
        self._append_log("===== 自动测时 =====")
        extra_args = self.var_extra_args.get().strip()
        startup_timeout = max(20, int(self.var_startup.get()))
        threading.Thread(
            target=self._calibrate_worker,
            args=(exe, extra_args, startup_timeout),
            daemon=False,
        ).start()

    def _resolve_exe_path(self) -> Path | None:
        if self.var_exe.get().strip():
            return Path(self.var_exe.get())
        from .locate import detect_game

        info = detect_game(
            Path(self.var_game_root.get()) if self.var_game_root.get() else None
        )
        return info.exe if info else None

    def _calibrate_worker(self, exe: Path, extra_args: str, startup_timeout: int) -> None:
        try:
            result = calibrate(
                exe,
                extra_args,
                startup_timeout=startup_timeout,
                emit_log=lambda text: self.event_queue.put(("log", text)),
                cancel_event=self.cancel_event,
            )
            if self.cancel_event.is_set():
                self.event_queue.put(("log", t("自动测时已取消。")))
                self.event_queue.put(("calibrated", {}))
            else:
                self.event_queue.put(("calibrated", result))
        except Exception as exc:  # noqa: BLE001
            self.event_queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, data = self.event_queue.get_nowait()
                self._handle_event(kind, data)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_event(self, kind: str, data: object) -> None:
        if kind == "log":
            self._append_log(str(data))
        elif kind == "status":
            self.status_var.set(str(data))
        elif kind == "progress":
            done, total, name = data
            self.progress["maximum"] = max(1, total)
            self.progress["value"] = done
            self.status_var.set(f"正在测试 ({done}/{total})：{name}")
        elif kind == "result":
            self._add_result(data)
        elif kind == "done":
            self._finish(data)
        elif kind == "error":
            self._fail(str(data))
        elif kind == "calibrated":
            self._calibrate_done(data)

    def _add_result(self, result: TestResult) -> None:
        self._row_index += 1
        tag = "warn"
        if result.verdict.value == "可用":
            tag = "ok"
        elif result.verdict.value == "不可用":
            tag = "fail"
        verdict_text = result.verdict.value
        verdict_map = {
            "可用": "verdict_ok",
            "不可用": "verdict_fail",
            "错误": "verdict_error",
            "已存在": "verdict_conflict",
            "跳过": "verdict_skipped",
        }
        if result.verdict.value in verdict_map:
            verdict_text = t(verdict_map[result.verdict.value])
        self.tree.insert(
            "",
            "end",
            values=(
                self._row_index,
                result.filename,
                verdict_text,
                f"{result.elapsed_seconds:.1f}",
                result.reason,
            ),
            tags=(tag,),
        )

    def _finish(self, summary: dict) -> None:
        self.running = False
        self.last_summary = summary
        self.btn_start.configure(state="normal")
        self.btn_calibrate.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_report.configure(state="normal")
        self.btn_quarantine.configure(state="normal")
        self.progress["value"] = summary.get("total", 0)
        self.status_var.set(
            f"完成：可用 {summary['ok']}，不可用 {summary['fail']}，错误 {summary['error']}，"
            f"已存在 {summary['conflict']}，跳过 {summary['skipped']}，共 {summary['total']}。"
        )
        self._append_log("===== 测试完成 =====")
        self._append_log(f"CSV 报告：{summary['csv_path']}")
        self._append_log(f"JSON 报告：{summary['json_path']}")
        messagebox.showinfo(
            t("测试完成"),
            t("测试已完成。") + "\n\n"
            f"可用 {summary['ok']} / 不可用 {summary['fail']} / 错误 {summary['error']}\n\n"
            f"报告目录：{Path(summary['csv_path']).parent}",
        )
        if self._close_when_done:
            self.root.destroy()

    def _calibrate_done(self, result: dict) -> None:
        self.calibrating = False
        self.btn_start.configure(state="normal")
        self.btn_calibrate.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        if not result:
            self.status_var.set(t("自动测时已取消。"))
            if self._close_when_done:
                self.root.destroy()
            return
        self.var_stable.set(int(result.get("suggested_stable", 35)))
        self._persist_stable(self.var_stable.get())
        window_s = result.get("window_seconds")
        idle_s = result.get("idle_seconds")
        self.status_var.set(
            f"自动测时完成：窗口 {window_s}s，主菜单(空闲) {idle_s}s，"
            f"建议稳定观察 {self.var_stable.get()}s。"
        )
        self._append_log(
            f"自动测时：窗口出现 {window_s}s，主菜单(空闲) {idle_s}s，"
            f"建议稳定观察 {self.var_stable.get()}s。"
        )
        messagebox.showinfo(
            t("自动测时完成"),
            f"游戏主窗口出现：{window_s} 秒\n"
            f"到主菜单(空闲)：{idle_s} 秒\n\n"
            f"已把“稳定观察”设为建议值 {self.var_stable.get()} 秒，并已自动保存。",
        )
        if self._close_when_done:
            self.root.destroy()

    def _persist_stable(self, value: int) -> None:
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if CONFIG_FILE.is_file():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        data["stable_seconds"] = int(value)
        try:
            CONFIG_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    def _fail(self, message: str) -> None:
        self.running = False
        self.calibrating = False
        self.btn_start.configure(state="normal")
        self.btn_calibrate.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_var.set(t("出错：") + message)
        self._append_log(t("错误：") + message)
        messagebox.showerror(t("测试出错"), message)
        if self._close_when_done:
            self.root.destroy()

    def _open_report(self) -> None:
        if self.last_summary and self.last_summary.get("csv_path"):
            os.startfile(str(Path(self.last_summary["csv_path"]).parent))  # type: ignore[attr-defined]
        elif self.var_report_dir.get().strip():
            Path(self.var_report_dir.get()).mkdir(parents=True, exist_ok=True)
            os.startfile(self.var_report_dir.get())  # type: ignore[attr-defined]

    def _open_tutorial(self) -> None:
        top = Toplevel(self.root)
        top.title(
            "Detailed Tutorial - RoN Mod Compatibility Tester"
            if get_language() == "en"
            else "详细使用教程 - RoN Mod 兼容性测试器"
        )
        top.geometry("760x680")
        top.minsize(620, 500)
        text = scrolledtext.ScrolledText(
            top, wrap="word", font=("Segoe UI", 10), state="normal"
        )
        text.pack(fill=BOTH, expand=True, padx=8, pady=8)
        text.insert(
            "1.0",
            TUTORIAL_TEXT_EN if get_language() == "en" else TUTORIAL_TEXT,
        )
        text.configure(state="disabled")
        top.transient(self.root)
        top.grab_set()

    def _choose_language(self) -> None:
        win = Toplevel(self.root)
        win.title(t("language"))
        win.geometry("260x140")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        def pick(lang: str) -> None:
            src = _key_for_label(_source_labels(), self.var_source.get(), "folder")
            mode = _key_for_label(_mode_labels(), self.var_mode.get(), "isolated")
            disp = _key_for_label(
                _disposition_labels(), self.var_disposition.get(), "quarantine"
            )
            set_language(lang)
            self._save_language(lang)
            self.var_source.set(_source_labels()[src])
            self.var_mode.set(_mode_labels()[mode])
            self.var_disposition.set(_disposition_labels()[disp])
            win.destroy()
            self._build_ui()

        ttk.Button(win, text="中文", command=lambda: pick("zh")).pack(
            fill=X, padx=24, pady=(24, 8)
        )
        ttk.Button(win, text="English", command=lambda: pick("en")).pack(
            fill=X, padx=24, pady=8
        )

    def _save_language(self, lang: str) -> None:
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if CONFIG_FILE.is_file():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        data["language"] = lang
        try:
            CONFIG_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    def _open_quarantine(self) -> None:
        path = self.last_summary.get("quarantine_dir") if self.last_summary else None
        if path and Path(path).is_dir():
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            messagebox.showinfo(t("隔离目录"), t("本次测试没有生成隔离目录或不可用 Mod。"))

    def _restore_backup(self) -> None:
        backup_dir = self._backup_dir()
        if backup_dir is None:
            messagebox.showwarning("未找到备份目录", "请先在“备份设置”里选择备份目录。")
            return
        if not (backup_dir / "manifest.json").is_file():
            messagebox.showwarning("未找到备份", f"未找到备份清单：{backup_dir}")
            return
        mod_dir = self._resolve_mod_dir()
        if mod_dir is None:
            messagebox.showwarning("未找到 Mod 目录", "请先自动检测或选择 Mod 安装目录。")
            return

        remove_new = BooleanVar(value=False)
        win = Toplevel(self.root)
        win.title("确认还原")
        win.geometry("520x250")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        ttk.Label(
            win,
            text=f"将从：\n{backup_dir}\n\n还原非系统 .pak 文件到：\n{mod_dir}",
            justify=LEFT,
        ).pack(anchor="w", padx=12, pady=(12, 6))
        ttk.Checkbutton(
            win,
            text="完全还原（同时移除备份后新增的非系统 Mod）",
            variable=remove_new,
        ).pack(anchor="w", padx=12, pady=6)

        result_holder: dict = {}

        def _confirm() -> None:
            win.destroy()
            try:
                restored, removed = restore_backup(
                    backup_dir, mod_dir, remove_new=bool(remove_new.get())
                )
            except (OSError, FileNotFoundError, json.JSONDecodeError) as exc:
                messagebox.showerror("还原失败", str(exc))
                return
            result_holder["restored"] = restored
            result_holder["removed"] = removed
            msg = f"已还原 {len(restored)} 个文件。"
            if remove_new.get():
                msg += f"\n已移除新增文件 {len(removed)} 个。"
            self._append_log("还原备份：" + msg)
            messagebox.showinfo("还原完成", msg)

        btns = ttk.Frame(win)
        btns.pack(fill=X, padx=12, pady=12)
        ttk.Button(btns, text="开始还原", command=_confirm).pack(side=LEFT, padx=6)
        ttk.Button(btns, text="取消", command=win.destroy).pack(side=LEFT, padx=6)

    def _backup_dir(self) -> Path | None:
        if self.var_backup_dir.get().strip():
            return Path(self.var_backup_dir.get())
        return default_backup_dir()

    def _open_backup_folder(self) -> None:
        backup_dir = self._backup_dir()
        if backup_dir and backup_dir.is_dir():
            os.startfile(str(backup_dir))  # type: ignore[attr-defined]
        else:
            messagebox.showinfo(t("备份目录"), t("还没有生成备份目录。"))

    def _open_backup_settings(self) -> None:
        old_dir = self.var_backup_dir.get()
        old_max_file = self.var_backup_max_file.get()
        old_max_total = self.var_backup_max_total.get()

        win = Toplevel(self.root)
        win.title("备份设置")
        win.geometry("520x240")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        frame = ttk.Frame(win, padding=12)
        frame.pack(fill=BOTH, expand=True)
        for col in range(3):
            frame.columnconfigure(col, weight=1)

        ttk.Checkbutton(
            frame, text="测试前备份 Mod 目录", variable=self.var_backup
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        ttk.Label(frame, text="备份目录").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(frame, textvariable=self.var_backup_dir).grid(
            row=1, column=1, sticky="ew", padx=4, pady=4
        )
        ttk.Button(
            frame,
            text="浏览…",
            command=lambda: self._browse_backup_dir(),
        ).grid(row=1, column=2, sticky="w", padx=4, pady=4)

        ttk.Label(frame, text="最大单文件(MB)").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        ttk.Spinbox(
            frame, from_=100, to=100000, textvariable=self.var_backup_max_file, width=12
        ).grid(row=2, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(frame, text="最大总大小(MB)").grid(row=3, column=0, sticky="e", padx=4, pady=4)
        ttk.Spinbox(
            frame, from_=100, to=1000000, textvariable=self.var_backup_max_total, width=12
        ).grid(row=3, column=1, sticky="w", padx=4, pady=4)

        btns = ttk.Frame(frame)
        btns.grid(row=4, column=0, columnspan=3, pady=(12, 0))

        def _ok() -> None:
            win.destroy()

        def _cancel() -> None:
            self.var_backup_dir.set(old_dir)
            self.var_backup_max_file.set(old_max_file)
            self.var_backup_max_total.set(old_max_total)
            win.destroy()

        ttk.Button(btns, text="确定", command=_ok).pack(side=LEFT, padx=6)
        ttk.Button(btns, text="取消", command=_cancel).pack(side=LEFT, padx=6)

    def _browse_backup_dir(self) -> None:
        path = filedialog.askdirectory(title="选择备份目录")
        if path:
            self.var_backup_dir.set(path)

    def _current_report_dir(self) -> Path | None:
        if self.var_report_dir.get().strip():
            return Path(self.var_report_dir.get())
        if self.var_mod_folder.get().strip():
            p = Path(self.var_mod_folder.get())
            return p.parent / (p.name + "_test_reports")
        return None

    def _resolve_mod_dir(self) -> Path | None:
        if self.var_mod_dir.get().strip():
            return Path(self.var_mod_dir.get())
        info = detect_game(
            Path(self.var_game_root.get()) if self.var_game_root.get() else None
        )
        if info is None:
            return None
        return detect_mod_dir(info)

    # ------------------------------------------------------------- config
    def _load_config(self) -> None:
        if not CONFIG_FILE.is_file():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for var, key in (
            (self.var_mod_folder, "mod_folder"),
            (self.var_game_root, "game_root"),
            (self.var_exe, "exe_path"),
            (self.var_mod_dir, "mod_dir"),
            (self.var_report_dir, "report_dir"),
            (self.var_extra_args, "extra_args"),
        ):
            if data.get(key):
                var.set(str(data[key]))
        self.var_stable.set(int(data.get("stable_seconds", 35)))
        self.var_startup.set(int(data.get("startup_timeout", 120)))
        self.var_menu_hold.set(int(data.get("menu_hold_seconds", 6)))
        saved_mode = data.get("mode", "isolated")
        self.var_mode.set(_mode_labels().get(saved_mode, _mode_labels()["isolated"]))
        self.var_warmup.set(bool(data.get("warmup", False)))
        self.var_close_running.set(bool(data.get("close_running", True)))
        self.var_backup.set(bool(data.get("backup_mods", True)))
        if data.get("backup_dir"):
            self.var_backup_dir.set(str(data["backup_dir"]))
        self.var_backup_max_file.set(int(data.get("backup_max_file_mb", 1500)))
        self.var_backup_max_total.set(int(data.get("backup_max_total_mb", 10000)))
        saved_source = data.get("source", "folder")
        self.var_source.set(_source_labels().get(saved_source, _source_labels()["folder"]))
        saved_disposition = data.get("disposition", "quarantine")
        self.var_disposition.set(
            _disposition_labels().get(saved_disposition, _disposition_labels()["quarantine"])
        )
        self.mod_files = [Path(p) for p in data.get("mod_files", [])]
        self.exclude_files = [Path(p) for p in data.get("exclude_files", [])]
        self._update_selection_label()

    def _save_config(self, config: AppConfig) -> None:
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        data = {
            "mod_folder": str(config.mod_folder) if config.mod_folder else "",
            "game_root": str(config.game_root) if config.game_root else "",
            "exe_path": str(config.exe_path) if config.exe_path else "",
            "mod_dir": str(config.mod_dir) if config.mod_dir else "",
            "report_dir": str(config.report_dir) if config.report_dir else "",
            "mod_files": [str(p) for p in config.mod_files],
            "exclude_files": [str(p) for p in config.exclude_files],
            "mode": config.mode,
            "stable_seconds": config.stable_seconds,
            "startup_timeout": config.startup_timeout,
            "menu_hold_seconds": config.menu_hold_seconds,
            "close_running": config.close_running,
            "backup_mods": config.backup_mods,
            "backup_dir": str(config.backup_dir) if config.backup_dir else "",
            "backup_max_file_mb": config.backup_max_file_mb,
            "backup_max_total_mb": config.backup_max_total_mb,
            "source": config.source,
            "disposition": config.disposition,
            "warmup": config.warmup,
            "extra_args": config.extra_args,
        }
        try:
            CONFIG_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    def _on_close(self) -> None:
        if not self.running and not self.calibrating:
            self.root.destroy()
            return
        if messagebox.askyesno(t("确认退出"), t("任务正在进行，是否停止并退出？")):
            self._close_when_done = True
            self.cancel_event.set()
            self.status_var.set(t("正在停止并退出…"))
            self.btn_stop.configure(state="disabled")
        # Otherwise keep the window open.


def main() -> int:
    root = Tk()
    if getattr(sys, "frozen", False):
        try:
            root.iconbitmap(sys.executable)
        except Exception:
            pass

    lang = None
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            lang = data.get("language")
        except (OSError, json.JSONDecodeError):
            lang = None

    if lang in ("zh", "en"):
        set_language(lang)
    else:
        # First launch: ask for language.
        choice: dict = {}
        chooser = Toplevel(root)
        chooser.title("Language / 语言")
        chooser.geometry("280x170")
        chooser.resizable(False, False)
        chooser.grab_set()

        def pick(value: str) -> None:
            choice["lang"] = value
            chooser.destroy()

        ttk.Label(chooser, text="Choose language / 选择语言").pack(
            pady=(22, 10)
        )
        ttk.Button(chooser, text="中文", command=lambda: pick("zh")).pack(
            fill=X, padx=30, pady=6
        )
        ttk.Button(chooser, text="English", command=lambda: pick("en")).pack(
            fill=X, padx=30, pady=6
        )
        root.wait_window(chooser)
        lang = choice.get("lang", "zh")
        set_language(lang)
        CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        try:
            CONFIG_FILE.write_text(
                json.dumps({"language": lang}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    app = App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
