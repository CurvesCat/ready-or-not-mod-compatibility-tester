from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Callable

from .models import DeployGroup, DeployPlan


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item]


def _parse_rules(rules: dict[str, Any]) -> tuple[dict[str, list[str]], list[list[str]]]:
    """Return (extra requires, explicit user groups)."""
    extra_requires: dict[str, list[str]] = {}
    user_groups: list[list[str]] = []
    mod_rules = rules.get("mods") or {}
    if isinstance(mod_rules, dict):
        for mod, spec in mod_rules.items():
            if not isinstance(spec, dict):
                continue
            requires = _as_list(spec.get("requires"))
            if requires:
                extra_requires[str(mod)] = requires
            group = _as_list(spec.get("group_with"))
            if group:
                user_groups.append([str(mod), *group])
    for group in rules.get("groups") or []:
        parsed = _as_list(group)
        if parsed:
            user_groups.append(parsed)
    return extra_requires, user_groups


def _union_find(names: list[str]) -> tuple[dict[str, int], list[set[str]]]:
    parent = {name: name for name in names}

    def find(item: str) -> str:
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != root:
            parent[item], item = root, parent[item]
        return root

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    return parent, (find, union)


def build_plan(
    static_report: dict[str, Any],
    dep_report: dict[str, Any] | None,
    rules: dict[str, Any] | None = None,
    log: Callable[[str], None] | None = None,
) -> DeployPlan:
    """Combine conflicts + dependency edges + user rules into deploy groups."""

    def emit(text: str) -> None:
        if log:
            log(text)

    rules = rules or {}
    scanned = [
        str(pak.get("filename"))
        for pak in static_report.get("paks") or []
        if pak.get("parse_ok", True)
    ]
    scanned_set = set(scanned)

    # overwrite conflicts from T1 static report
    conflict_pairs: list[list[str]] = []
    conflict_set: set[frozenset[str]] = set()
    for conflict in static_report.get("conflicts") or []:
        if conflict.get("kind") != "overwrite":
            continue
        mods = [
            str(provider.get("filename"))
            for provider in conflict.get("providers") or []
        ]
        mods = [name for name in mods if name in scanned_set]
        if len(mods) < 2:
            continue
        key = frozenset(mods[:2])
        if key not in conflict_set:
            conflict_set.add(key)
            conflict_pairs.append([mods[0], mods[1]])

    requires: dict[str, set[str]] = defaultdict(set)
    extra_requires, user_groups = _parse_rules(rules)
    for mod, reqs in extra_requires.items():
        for req in reqs:
            if req in scanned_set and mod in scanned_set:
                requires[mod].add(req)

    for edge in (dep_report or {}).get("edges") or []:
        source = str(edge.get("from_mod"))
        target = str(edge.get("to_mod"))
        if source in scanned_set and target in scanned_set:
            requires[source].add(target)

    names = sorted(scanned_set)
    parent, (find, union) = _union_find(names)

    # Dependency edges connect a mod with everything it requires.
    for source, targets in requires.items():
        for target in targets:
            union(source, target)

    # Explicit user groups always stay together.
    for group in user_groups:
        present = [name for name in group if name in scanned_set]
        for index in range(1, len(present)):
            union(present[0], present[index])

    components: dict[str, list[str]] = defaultdict(list)
    for name in names:
        components[find(name)].append(name)
    ordered_components = [
        sorted(component) for component in components.values()
    ]
    ordered_components.sort(key=lambda component: (component[0].lower(), len(component)))

    warnings: list[str] = []
    groups: list[DeployGroup] = []
    conflict_mod_set: set[str] = {
        name for pair in conflict_pairs for name in pair
    }

    for index, component in enumerate(ordered_components, start=1):
        if len(component) == 1:
            reason = "isolated"
            evidence: list[str] = []
        else:
            reasons = set()
            for source in component:
                if source in requires:
                    reasons.add("dependency")
            for group in user_groups:
                if len([name for name in group if name in component]) > 1:
                    reasons.add("user_group")
            for source in component:
                for target in requires.get(source, set()):
                    if target in component:
                        reasons.add("dependency")
            reason = (
                "user_group"
                if "user_group" in reasons
                else ("dependency" if reasons else "strong_dependency")
            )
            evidence = [
                f"{source} requires {target}"
                for source in component
                for target in sorted(requires.get(source, set()))
                if target in component
            ]
            in_component_conflict = [
                pair for pair in conflict_pairs if pair[0] in component and pair[1] in component
            ]
            if in_component_conflict:
                warnings.append(
                    "同组 Mod 存在静态覆盖冲突，测试结果可能无法归因到单个 Mod："
                    + "; ".join(" <-> ".join(pair) for pair in in_component_conflict)
                )

        if len(component) > 1 or reason != "isolated":
            groups.append(
                DeployGroup(
                    group_id=f"g{index}",
                    mods=component,
                    reason=reason,
                    evidence=evidence,
                )
            )
        else:
            groups.append(
                DeployGroup(
                    group_id=f"g{index}",
                    mods=component,
                    reason="isolated",
                    evidence=[],
                )
            )

    if conflict_mod_set:
        emit(f"冲突涉及 {len(conflict_mod_set)} 个 Mod，已保留为独立计划组。")

    return DeployPlan(
        mods=names,
        groups=groups,
        conflict_pairs=conflict_pairs,
        warnings=warnings,
    )
