from __future__ import annotations

import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from . import APP_NAME, AUTHOR, VERSION, default_backup_dir
from .engine import DeployItem, GameSession, SessionResult
from .locate import build_game_info, detect_game, detect_mod_dir
from .models import AppConfig, GameInfo, TestResult, Verdict
from .proc import (
    close_error_windows,
    find_game_processes,
    graceful_close,
    is_steam_running,
)
from .report import write_reports
from .safety import (
    create_backup,
    list_mod_paks,
    snapshot_mod_dir,
    verify_dir_state,
)


EmitFn = Callable[[str, Any], None]


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _unique_destination(directory: Path, filename: str) -> Path:
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError(f"不安全的文件名：{filename!r}")
    target = directory / filename
    if not target.exists():
        return target
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _query_crash_events(exe_stem: str, since: datetime) -> list[str]:
    cmd = (
        "Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=("
        f"Get-Date -Date '{since.isoformat()}')"
        "; Id=1000,1001} -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.Message -match '{exe_stem}' }} | "
        "Select-Object -First 3 -ExpandProperty Message"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()][:3]
    except (OSError, subprocess.TimeoutExpired):
        return []


class TestRunner:
    def __init__(
        self,
        config: AppConfig,
        emit: EmitFn,
        cancel_event: Any,
    ) -> None:
        self.config = config
        self.emit = emit
        self.cancel_event = cancel_event
        self.results: list[TestResult] = []
        self._current_session: GameSession | None = None
        self._resolved = 0
        self._total = 0
        self._mod_dir: Path | None = None
        self._exe_path: Path | None = None
        self._quarantine_dir: Path | None = None
        self._log_dir: Path | None = None
        self._crashes_dir: Path | None = None
        self._existing_names: set[str] = set()
        self._apply_disposition = True
        self._installed_items: list[DeployItem] = []
        self._park_dir: Path | None = None
        self._restore_installed = False

    # ------------------------------------------------------------------ utils
    def _log(self, text: str) -> None:
        self.emit("log", text)

    def _cancelled(self) -> bool:
        return bool(self.cancel_event and self.cancel_event.is_set())

    def _new_session(self, stable_seconds: int, menu_hold_seconds: int) -> GameSession:
        return GameSession(
            exe_path=self._exe_path,
            mod_dir=self._mod_dir,
            log_dir=self._log_dir,
            crashes_dir=self._crashes_dir,
            stable_seconds=stable_seconds,
            startup_timeout=self.config.startup_timeout,
            menu_hold_seconds=menu_hold_seconds,
            close_timeout=self.config.close_timeout,
            extra_args=self.config.extra_args,
            emit_log=self._log,
            cancel_event=self.cancel_event,
        )

    def _run_session(self, items: list[DeployItem], label: str) -> SessionResult:
        if self._cancelled():
            return SessionResult(Verdict.SKIPPED, reason="用户取消")
        if self.config.mode == "strict":
            stable = max(self.config.stable_seconds, 60)
            menu_hold = 10**9
        else:
            stable = self.config.stable_seconds
            menu_hold = self.config.menu_hold_seconds
        session = self._new_session(stable, menu_hold)
        self._current_session = session
        try:
            return session.run(items, label)
        finally:
            self._current_session = None

    def _emit_progress(self, label: str) -> None:
        self.emit("progress", (self._resolved, self._total, label))

    def _resolve(
        self,
        item: DeployItem,
        verdict: Verdict,
        reason: str,
        excerpt: str,
        elapsed: float,
        *,
        menu_reached: bool = False,
        crash_dirs: list[str] | None = None,
    ) -> TestResult:
        result = TestResult(
            filename=item.source.name,
            source_path=item.source,
            verdict=verdict,
            elapsed_seconds=elapsed,
            reason=reason,
            log_excerpt=excerpt,
            started_at=datetime.now().isoformat(timespec="seconds"),
            finished_at=datetime.now().isoformat(timespec="seconds"),
            deployed_path=item.target_path,
            mod_dir=str(self._mod_dir),
            exe=str(self._exe_path),
        )
        result.details["mode"] = self.config.mode
        result.details["source"] = self.config.source
        result.details["disposition"] = self.config.disposition
        result.details["menu_reached"] = menu_reached
        if crash_dirs:
            result.details["crash_dirs"] = crash_dirs

        if verdict == Verdict.FAIL and not excerpt:
            events = _query_crash_events(
                self._exe_path.stem, datetime.now() - timedelta(minutes=3)
            )
            if events:
                result.log_excerpt = events[0][:800]
                result.details["windows_events"] = events

        if verdict == Verdict.FAIL and self._apply_disposition:
            self._dispose_folder(item.source, result)

        self.results.append(result)
        self._resolved += 1
        self._emit_progress(item.source.name)
        self.emit("result", result)
        return result

    def _dispose_folder(self, source: Path, result: TestResult) -> None:
        disposition = self.config.disposition
        try:
            if disposition == "quarantine":
                target = _unique_destination(self._quarantine_dir, source.name)
                shutil.move(str(source), str(target))
                result.quarantined_path = target
                self._log(f"  已移入隔离区：{target}")
            elif disposition == "disable":
                target = _unique_destination(source.parent, source.name + ".disabled")
                shutil.move(str(source), str(target))
                result.details["disabled_path"] = str(target)
                self._log(f"  已禁用（重命名）：{target}")
            elif disposition == "delete":
                source.unlink(missing_ok=True)
                result.details["deleted"] = True
                self._log(f"  已删除：{source.name}")
        except OSError as exc:
            self._log(f"  无法执行“{disposition}”：{exc}")

    def _apply_exclude(self, files: list[Path]) -> list[Path]:
        excluded = {p.resolve() for p in self.config.exclude_files}
        if not excluded:
            return files
        return [p for p in files if p.resolve() not in excluded]

    # --------------------------------------------------------------- run
    def run(self) -> dict[str, Any]:
        cfg = self.config
        emit = self.emit
        emit("status", "正在初始化…")

        if (
            cfg.source == "folder"
            and not cfg.mod_files
            and (not cfg.mod_folder or not cfg.mod_folder.is_dir())
        ):
            raise RuntimeError("请选择 Mod 文件夹，或手动添加至少一个 .pak 文件。")

        game_info: GameInfo | None
        if cfg.game_root:
            if not cfg.game_root.is_dir():
                raise RuntimeError(f"所选游戏根目录不存在：{cfg.game_root}")
            game_info = build_game_info(cfg.game_root)
            if game_info is None:
                raise RuntimeError(
                    "所选游戏根目录无效：未找到 ReadyOrNot\\Content\\Paks 或 "
                    "ReadyOrNot\\Binaries\\Win64。"
                )
        else:
            self._log("正在自动检测《严阵以待》安装目录…")
            game_info = detect_game()
        if game_info is None:
            raise RuntimeError(
                "未能自动检测到游戏目录。请手动选择游戏根目录（包含 ReadyOrNot 文件夹）。"
            )

        if cfg.exe_path:
            if not cfg.exe_path.is_file():
                raise RuntimeError(f"找不到游戏可执行文件：{cfg.exe_path}")
            exe_path = cfg.exe_path
        else:
            exe_path = game_info.exe
        if not exe_path.is_file():
            raise RuntimeError(f"找不到游戏可执行文件：{exe_path}")

        if cfg.mod_dir and not cfg.mod_dir.is_dir():
            raise RuntimeError(f"所选 Mod 安装目录不存在：{cfg.mod_dir}")
        mod_dir = detect_mod_dir(game_info, cfg.mod_dir)
        if mod_dir is None:
            raise RuntimeError(f"找不到游戏 Paks 目录：{game_info.paks_dir}")
        mod_dir = _ensure_dir(mod_dir)

        if cfg.source == "installed":
            default_report = game_info.root.parent / "RoN_ModCompat_Reports"
        elif cfg.mod_folder:
            default_report = cfg.mod_folder.parent / (
                cfg.mod_folder.name + "_test_reports"
            )
        else:
            default_report = cfg.mod_files[0].parent / "RoN_ModCompat_Reports"
        report_dir = _ensure_dir(cfg.report_dir or default_report)
        log_dir = _ensure_dir(report_dir / "logs")
        quarantine_dir = _ensure_dir(report_dir / "quarantine")

        self._mod_dir = mod_dir
        self._exe_path = exe_path
        self._log_dir = log_dir
        self._quarantine_dir = quarantine_dir
        self._crashes_dir = game_info.crashes_dir
        self._existing_names = {p.name for p in mod_dir.iterdir()}

        self._log(f"游戏目录：{game_info.root}")
        self._log(f"可执行文件：{exe_path.name}")
        self._log(f"Mod 安装目录：{mod_dir}")
        self._log(f"报告目录：{report_dir}")
        self._log(f"测试来源：{'游戏目录内已安装' if cfg.source == 'installed' else '候选文件夹'}")
        self._log(f"测试策略：{self._mode_label(cfg.mode)}")

        if not is_steam_running():
            self._log("警告：未检测到 Steam 正在运行，游戏可能无法通过 Steam 校验。")

        running = find_game_processes(exe_path)
        if running:
            if not cfg.close_running:
                raise RuntimeError(
                    "游戏进程已在运行。请先退出游戏，或勾选“测试前关闭已运行的游戏”。"
                )
            self._log("检测到游戏正在运行，正在关闭…")
            graceful_close(running, timeout=max(6, cfg.close_timeout))
            time.sleep(1.0)

        before = snapshot_mod_dir(mod_dir)
        backup_root = cfg.backup_dir or default_backup_dir()
        backup_dir, manifest_path = create_backup(
            mod_dir,
            backup_root,
            backup_enabled=cfg.backup_mods,
            max_file_bytes=cfg.backup_max_file_mb * 1024 * 1024,
            max_total_bytes=cfg.backup_max_total_mb * 1024 * 1024,
        )
        self._log(f"已保存 Mod 目录状态清单：{manifest_path}")
        if cfg.backup_mods:
            self._log(f"已创建备份目录：{backup_dir}")

        # Build the list of items to test.
        if cfg.source == "installed":
            installed = self._apply_exclude(list_mod_paks(mod_dir))
            if not installed:
                raise RuntimeError("游戏 Mod 目录中没有检测到已安装的非系统 .pak Mod。")
            self._log(f"检测到已安装 Mod {len(installed)} 个，正在移入临时区…")
            park_dir = _ensure_dir(
                report_dir / f"inplace_parked_{datetime.now():%Y%m%d-%H%M%S}"
            )
            self._park_installed(installed, park_dir)
            items = list(self._installed_items)
            self._apply_disposition = False
            self._restore_installed = True
            self._log("已移出，开始测试…")
        else:
            mod_files: list[Path] = []
            if cfg.mod_folder and cfg.mod_folder.is_dir():
                mod_files = list_mod_paks(cfg.mod_folder, exclude=report_dir)
            for path in cfg.mod_files:
                if path.is_file() and path not in mod_files:
                    mod_files.append(path)
            mod_files = self._apply_exclude(mod_files)
            if not mod_files:
                raise RuntimeError("所选文件夹中没有检测到非系统 .pak Mod 文件。")
            items = [DeployItem(source=p, target_name=p.name) for p in mod_files]
            self._apply_disposition = True

        self._total = len(items)
        self._log(f"待测试 Mod：{self._total} 个")

        summary = {
            "app": APP_NAME,
            "version": VERSION,
            "author": AUTHOR,
            "game_root": str(game_info.root),
            "exe": str(exe_path),
            "mod_dir": str(mod_dir),
            "mod_folder": (
                str(cfg.mod_folder)
                if cfg.mod_folder
                else ("(游戏目录内已安装)" if cfg.source == "installed" else "(手动选择文件)")
            ),
            "mode": cfg.mode,
            "source": cfg.source,
            "disposition": cfg.disposition,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "stable_seconds": cfg.stable_seconds,
            "startup_timeout": cfg.startup_timeout,
            "menu_hold_seconds": cfg.menu_hold_seconds,
            "warmup": cfg.warmup,
            "total": self._total,
            "ok": 0,
            "fail": 0,
            "error": 0,
            "conflict": 0,
            "skipped": 0,
            "results": [],
        }

        try:
            if cfg.warmup:
                self._log("开始预热：不带 Mod 启动一次游戏…")
                warm = self._run_session([], "warmup")
                if warm.verdict != Verdict.OK:
                    raise RuntimeError(
                        "预热失败：干净状态下游戏无法正常启动。请检查游戏本体/Steam。"
                    )
                self._log("预热完成。")

            self._run_isolated(items)
        finally:
            if self._current_session:
                self._current_session.cleanup()
            leftover = find_game_processes(exe_path)
            if leftover:
                graceful_close(leftover, timeout=max(6, cfg.close_timeout))
            close_error_windows(ignore_titles=(APP_NAME,))

            if self._restore_installed:
                self._restore_installed_mods()

            if self._park_dir and self._park_dir.exists():
                try:
                    self._park_dir.rmdir()
                    self._park_dir = None
                except OSError:
                    pass

            if cfg.source == "installed":
                self._log("就地测试完成，已按处理方式恢复/隔离/禁用/删除对应 Mod。")
            else:
                diffs = verify_dir_state(mod_dir, before)
                if diffs:
                    self._log("警告：Mod 目录状态与测试前不一致，请人工检查：")
                    for diff in diffs:
                        self._log("  - " + diff)
                else:
                    self._log("Mod 目录状态校验通过，未改动原有文件。")

            summary["results"] = [r.as_dict() for r in self.results]
            for result in self.results:
                key = result.verdict.name.lower()
                if key in summary:
                    summary[key] += 1
            summary["finished_at"] = datetime.now().isoformat(timespec="seconds")

            csv_path, json_path = write_reports(
                report_dir,
                summary=summary,
                results=self.results,
                config=cfg,
            )
            summary["csv_path"] = str(csv_path)
            summary["json_path"] = str(json_path)
            summary["backup_dir"] = str(backup_dir)
            summary["quarantine_dir"] = str(quarantine_dir)
            if self._park_dir:
                summary["park_dir"] = str(self._park_dir)
            emit("done", summary)
        return summary

    @staticmethod
    def _mode_label(mode: str) -> str:
        return {
            "isolated": "标准隔离（逐个测试）",
            "strict": "严格深度（逐个，更长观察）",
        }.get(mode, mode)

    # ----------------------------------------------------- installed handling
    def _park_installed(self, installed: list[Path], park_dir: Path) -> None:
        moved: list[tuple[Path, Path]] = []
        try:
            for original in installed:
                target = park_dir / original.name
                shutil.move(str(original), str(target))
                moved.append((original, target))
        except OSError as exc:
            for original, target in reversed(moved):
                try:
                    shutil.move(str(target), str(original))
                except OSError:
                    pass
            raise RuntimeError(f"无法移出已安装 Mod：{exc}")
        self._installed_items = [
            DeployItem(source=target, target_name=original.name)
            for original, target in moved
        ]
        self._park_dir = park_dir

    def _restore_installed_mods(self) -> None:
        result_map = {r.source_path.resolve(): r for r in self.results}
        for item in self._installed_items:
            parked = item.source
            if not parked.exists():
                self._log(f"  未找到临时文件：{parked.name}")
                continue
            result = result_map.get(parked.resolve())
            verdict = result.verdict if result else Verdict.SKIPPED
            if verdict == Verdict.FAIL:
                self._dispose_installed(parked, item.target_name)
            else:
                self._restore_one(parked, item.target_name)
        self._restore_installed = False

    def _restore_one(self, parked: Path, original_name: str) -> None:
        target = _unique_destination(self._mod_dir, original_name)
        try:
            shutil.move(str(parked), str(target))
            self._log(f"  已恢复：{target.name}")
        except OSError as exc:
            self._log(f"  无法恢复 {parked.name}：{exc}")

    def _dispose_installed(self, parked: Path, original_name: str) -> None:
        disposition = self.config.disposition
        try:
            if disposition == "quarantine":
                target = _unique_destination(self._quarantine_dir, original_name)
                shutil.move(str(parked), str(target))
                self._log(f"  已移入隔离区：{target}")
            elif disposition == "disable":
                target = _unique_destination(
                    self._mod_dir, original_name + ".disabled"
                )
                shutil.move(str(parked), str(target))
                self._log(f"  已禁用（重命名）：{target.name}")
            elif disposition == "delete":
                parked.unlink(missing_ok=True)
                self._log(f"  已删除：{original_name}")
            else:  # record
                self._restore_one(parked, original_name)
        except OSError as exc:
            self._log(f"  无法执行“{disposition}”：{exc}")
            self._restore_one(parked, original_name)

    # ------------------------------------------------------- isolated strategy
    def _run_isolated(self, items: list[DeployItem]) -> None:
        for index, item in enumerate(items, start=1):
            if self._cancelled():
                self._log("已请求停止，未完成的 Mod 标记为跳过。")
                for remaining in items[index - 1 :]:
                    self._resolve(
                        remaining,
                        Verdict.SKIPPED,
                        "已取消，未完成测试",
                        "",
                        0.0,
                    )
                return
            self._log(f"[{index}/{len(items)}] 正在测试：{item.source.name}")
            self._test_single(item, item.source.name)

    def _test_single(self, item: DeployItem, label: str) -> None:
        target_exists = (self._mod_dir / item.target_name).exists()
        if target_exists and item.target_name == item.source.name:
            self._resolve(
                item,
                Verdict.CONFLICT,
                "Mod 目录中已存在同名文件，已跳过（未覆盖）。",
                "",
                0.0,
            )
            return
        result = self._run_session([item], label)
        self._log(
            f"  → {result.verdict.value}"
            + (f"：{result.reason}" if result.reason else "")
        )
        self._resolve(
            item,
            result.verdict,
            result.reason,
            result.excerpt,
            result.elapsed_seconds,
            menu_reached=result.menu_reached,
            crash_dirs=result.crash_dirs,
        )

    # ---------------------------------------------------------- batch strategy
    def _assign_batch_names(self, mod_files: list[Path]) -> list[DeployItem]:
        used = set(self._existing_names)
        items: list[DeployItem] = []
        for idx, source in enumerate(mod_files):
            if source.name not in used:
                target = source.name
                used.add(target)
            else:
                target = f"_roncct_{idx + 1}_{source.stem}.pak"
                while target in used:
                    target = f"_roncct_{idx + 1}_{source.stem}_{idx + 2}.pak"
                used.add(target)
            items.append(DeployItem(source=source, target_name=target))
        return items

    def _run_batch(self, items: list[DeployItem]) -> None:
        working = list(items)
        round_no = 0
        while working and not self._cancelled():
            round_no += 1
            self._log(f"合并启动测试剩余 {len(working)} 个 Mod…")
            self._emit_progress(f"合并测试剩余 {len(working)} 个（第 {round_no} 轮启动）")
            result = self._run_session(working, f"batch_{len(working)}")
            if result.verdict == Verdict.SKIPPED:
                for item in working:
                    self._resolve(
                        item,
                        Verdict.SKIPPED,
                        "已取消，未完成测试",
                        "",
                        0.0,
                    )
                working = []
                break
            if result.verdict == Verdict.OK:
                for item in working:
                    self._log(f"  {item.source.name} → 可用（批量通过）")
                    self._resolve(
                        item,
                        Verdict.OK,
                        "批量测试通过"
                        + ("（检测到主菜单标记）" if result.menu_reached else ""),
                        result.excerpt,
                        result.elapsed_seconds,
                        menu_reached=result.menu_reached,
                    )
                working = []
                break
            if result.verdict == Verdict.ERROR:
                self._log(f"  合并启动出错：{result.reason}，剩余 Mod 标记为错误。")
                for item in working:
                    self._resolve(
                        item,
                        Verdict.ERROR,
                        result.reason,
                        result.excerpt,
                        result.elapsed_seconds,
                    )
                working = []
                break
            if result.verdict == Verdict.CONFLICT:
                self._log("  合并部署遇到同名冲突，改为逐个复核。")
                for item in working:
                    if self._cancelled():
                        break
                    self._test_single(item, item.source.name)
                working = []
                break

            bad = self._isolate_bad(working)
            if bad is None:
                self._log("  二分无法定位，可能存在 Mod 相互影响，改为逐个复核。")
                for item in working:
                    if self._cancelled():
                        break
                    self._test_single(item, item.source.name)
                working = []
                break

            self._log(f"  定位到问题 Mod：{bad.source.name}（{result.reason}）")
            self._resolve(
                bad,
                Verdict.FAIL,
                result.reason,
                result.excerpt,
                result.elapsed_seconds,
                menu_reached=result.menu_reached,
                crash_dirs=result.crash_dirs,
            )
            working.remove(bad)

    def _isolate_bad(self, items: list[DeployItem]) -> DeployItem | None:
        if len(items) == 1:
            return items[0]
        mid = len(items) // 2
        first = items[:mid]
        second = items[mid:]

        res_first = self._run_session(first, f"bisect_{len(first)}")
        if res_first.verdict == Verdict.FAIL:
            return self._isolate_bad(first)
        if res_first.verdict == Verdict.ERROR:
            return None

        res_second = self._run_session(second, f"bisect_{len(second)}")
        if res_second.verdict == Verdict.FAIL:
            return self._isolate_bad(second)
        if res_second.verdict == Verdict.ERROR:
            return None

        return None
