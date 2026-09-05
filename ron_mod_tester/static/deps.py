from __future__ import annotations

import tempfile
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .asset_worker import UAssetCliReader
from .models import PakFileEntry, PakInventory
from .pak_repak import RepakBackend


def _ue_path_from_file(path: str) -> str:
    """Map a repak path like ReadyOrNot/Content/Mods/X/Y.uasset to /Game/Mods/X/Y."""
    normalized = path.replace("\\", "/")
    for prefix in ("ReadyOrNot/Content/", "Content/"):
        if normalized.startswith(prefix):
            stem = normalized[len(prefix) :]
            for suffix in (".uasset", ".uexp", ".ubulk", ".uptnl"):
                if stem.endswith(suffix):
                    stem = stem[: -len(suffix)]
                    break
            return "/Game/" + stem
    return normalized


def _uasset_stems(inventory: PakInventory) -> list[str]:
    stems: set[str] = set()
    for entry in inventory.entries:
        path = entry.internal_path
        if path.endswith(".uasset"):
            stems.add(path[: -len(".uasset")])
    return sorted(stems)


def _asset_provider_map(
    inventories: list[PakInventory],
) -> dict[str, list[tuple[str, PakInventory]]]:
    provider_map: dict[str, list[tuple[str, PakInventory]]] = defaultdict(list)
    for inv in inventories:
        for stem in _uasset_stems(inv):
            provider_map[_ue_path_from_file(stem + ".uasset")].append(
                (inv.filename, inv)
            )
    return provider_map


def _match_ref_to_provider(
    ref: str,
    provider_map: dict[str, list[tuple[str, PakInventory]]],
    current_mod: str,
) -> tuple[str | None, str]:
    """Return (mod_name, confidence) for a UE import path, if a scanned mod provides it."""
    ref = ref.strip()
    if not ref.startswith("/Game"):
        return None, ""
    if ":" in ref:
        ref = ref.split(":", 1)[0]
    candidates = [ref]
    # An import can point at Package.Asset or Package.Asset:Object while we only
    # know the package path. Try progressively shorter dot suffixes.
    for provider_path in provider_map:
        if ref == provider_path:
            candidates = [ref]
            break
        if ref.startswith(provider_path + ".") or ref.startswith(provider_path + "_C"):
            candidates.append(provider_path)

    seen: set[str] = set()
    for candidate in candidates:
        for mod_name, _inv in provider_map.get(candidate, []):
            if mod_name == current_mod:
                continue
            key = (candidate, mod_name)
            if key in seen:
                continue
            seen.add(key)
            confidence = "high" if candidate == ref else "medium"
            return mod_name, confidence
    return None, ""


def _collect_refs(parsed: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for imp in parsed.get("Imports") or []:
        if not isinstance(imp, dict):
            continue
        name = imp.get("ObjectName") or ""
        if isinstance(name, str) and name.startswith(("/Game", "/ReadyOrNot")):
            refs.append(name)
    soft = parsed.get("SoftPackageReferenceList") or []
    for item in soft:
        if isinstance(item, str) and item.startswith(("/Game", "/ReadyOrNot")):
            refs.append(item)
    return refs


def scan_dependencies(
    folder: Path,
    *,
    repak_exe: str | Path,
    dotnet_exe: str | Path,
    uasset_cli_dll: str | Path,
    engine: str = "VER_UE5_4",
    asset_limit: int = 0,
    workers: int = 4,
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Parse uasset import tables and build cross-pak dependency edges."""

    def emit(text: str) -> None:
        if log:
            log(text)

    from .analyzer import _iter_paks

    backend = RepakBackend(repak_exe)
    paks = _iter_paks(folder)
    emit(f"检测到 {len(paks)} 个非系统 .pak")

    inventories: list[PakInventory] = []
    for index, pak in enumerate(paks, start=1):
        info = backend.info(pak)
        paths = backend.list_paths(pak)
        inventories.append(
            PakInventory(
                pak_path=pak,
                filename=pak.name,
                size_bytes=pak.stat().st_size,
                mount_point=str(info.get("mount point", "")),
                pak_version=str(info.get("version", "")),
                backend=backend.name,
                entry_count=len(paths),
                entries=[PakFileEntry(internal_path=p) for p in paths],
            )
        )
        emit(f"  [{index}/{len(paks)}] {pak.name}: {len(paths)} 个条目")

    provider_map = _asset_provider_map(inventories)
    reader = UAssetCliReader(dotnet_exe, uasset_cli_dll, engine=engine)
    edges: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    parsed_assets = 0

    for inv in inventories:
        stems = _uasset_stems(inv)
        if asset_limit > 0:
            stems = stems[:asset_limit]
        emit(f"{inv.filename}: 解析 {len(stems)} 个资产…")

        def handle_stem(
            stem: str,
        ) -> tuple[bool, list[tuple[str, str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
            """Return (ok, refs, unresolved, errors)."""
            uasset_file = stem + ".uasset"
            uexp_file = stem + ".uexp"
            try:
                uasset_data = backend.read_file(inv.pak_path, uasset_file)
                uexp_data = None
                has_uexp = uexp_file in {e.internal_path for e in inv.entries}
                if has_uexp:
                    uexp_data = backend.read_file(inv.pak_path, uexp_file)
            except RuntimeError as exc:
                return (
                    False,
                    [],
                    [],
                    [{"mod": inv.filename, "asset": stem, "error": str(exc)}],
                )

            temp_root = Path(tempfile.gettempdir()) / "ronct_t2"
            temp_root.mkdir(parents=True, exist_ok=True)
            unique = uuid.uuid4().hex
            tmp_asset = temp_root / f"{inv.filename}_{unique}.uasset"
            tmp_uexp = temp_root / f"{inv.filename}_{unique}.uexp"
            try:
                tmp_asset.write_bytes(uasset_data)
                if uexp_data is not None:
                    tmp_uexp.write_bytes(uexp_data)
                parsed = reader.parse_file(
                    tmp_asset,
                    tmp_uexp if uexp_data is not None else None,
                    temp_root,
                )
            except (RuntimeError, OSError) as exc:
                return (
                    False,
                    [],
                    [],
                    [{"mod": inv.filename, "asset": stem, "error": str(exc)}],
                )
            finally:
                try:
                    tmp_asset.unlink(missing_ok=True)
                    if tmp_uexp.exists():
                        tmp_uexp.unlink()
                except OSError:
                    pass

            my_refs: list[tuple[str, str, str]] = []
            my_unresolved: list[dict[str, Any]] = []
            for ref in _collect_refs(parsed):
                if ref.startswith(_ue_path_from_file(stem + ".uasset")):
                    continue
                mod_name, confidence = _match_ref_to_provider(
                    ref, provider_map, inv.filename
                )
                if mod_name:
                    my_refs.append((mod_name, confidence, ref))
                elif ref.startswith("/Game/Mods/"):
                    my_unresolved.append(
                        {
                            "mod": inv.filename,
                            "asset": stem,
                            "ref": ref,
                            "reason": "not_provided_by_scanned_mods",
                        }
                    )
            return True, my_refs, my_unresolved, []

        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [pool.submit(handle_stem, stem) for stem in stems]
            done = 0
            for future in as_completed(futures):
                done += 1
                ok, refs, unresolved_for_asset, errs = future.result()
                if ok:
                    parsed_assets += 1
                for mod, confidence, ref in refs:
                    key = (inv.filename, mod, confidence, ref)
                    if key not in edges:
                        edges[key] = {
                            "from_mod": inv.filename,
                            "to_mod": mod,
                            "confidence": confidence,
                            "asset_path": ref,
                        }
                unresolved.extend(unresolved_for_asset)
                parse_errors.extend(errs)
                if done % 25 == 0 or done == len(stems):
                    emit(f"    进度 {done}/{len(stems)}")

    # SCC on unique from->to pairs.
    graph: dict[str, set[str]] = defaultdict(set)
    for edge in edges.values():
        if edge["to_mod"] != edge["from_mod"]:
            graph[edge["from_mod"]].add(edge["to_mod"])
    components = _strong_connected_components(graph)

    emit("依赖解析完成。")
    return {
        "schema": "ronct.deps.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "backend": {"pak": backend.name, "asset": "uassetapi", "engine": engine},
        "paks": [inv.as_dict() for inv in inventories],
        "parsed_assets": parsed_assets,
        "edges": list(edges.values()),
        "unresolved_refs": unresolved,
        "parse_errors": parse_errors,
        "strongly_connected_components": components,
    }


def _strong_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    if not graph:
        return []
    # Every edge target must also be a node in the graph.
    for source in list(graph.keys()):
        for target in list(graph.get(source, set())):
            graph.setdefault(target, set())
    nodes = list(graph.keys())
    index = 0
    stack: list[str] = []
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    result: list[list[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for neighbor in graph.get(node, set()):
            if neighbor not in indices:
                strongconnect(neighbor)
                lowlink[node] = min(lowlink[node], lowlink[neighbor])
            elif neighbor in on_stack:
                lowlink[node] = min(lowlink[node], indices[neighbor])
        if lowlink[node] == indices[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            result.append(component)

    for node in nodes:
        if node not in indices:
            strongconnect(node)
    return sorted(
        (sorted(component) for component in result if len(component) > 1),
        key=lambda component: component[0],
    )
