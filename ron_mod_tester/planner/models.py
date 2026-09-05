from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeployUnit:
    filename: str


@dataclass
class DeployGroup:
    """One game launch: all units in this group are installed together."""

    group_id: str
    mods: list[str]
    reason: str  # isolated | dependency | strong_dependency | user_group
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "mods": self.mods,
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass
class DeployPlan:
    mods: list[str]
    groups: list[DeployGroup]
    conflict_pairs: list[list[str]]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "ronct.plan.v1",
            "mods": self.mods,
            "deploy_groups": [group.as_dict() for group in self.groups],
            "conflict_pairs": self.conflict_pairs,
            "warnings": self.warnings,
        }
