"""Structural validation for serialized and in-flight game states."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.engine.core.geometry import Polygon
from backend.engine.core.models import SCHEMA_VERSION, GameState, Side


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in ("error", "warning"):
            raise ValueError("severity must be 'error' or 'warning'")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "data": self.data,
        }


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def add(
        self,
        code: str,
        message: str,
        severity: str = "error",
        **data: Any,
    ) -> None:
        self.issues.append(
            ValidationIssue(code=code, message=message, severity=severity, data=data)
        )

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        self.issues.extend(other.issues)
        return self

    def raise_for_errors(self) -> None:
        if not self.ok:
            details = "; ".join(issue.message for issue in self.errors)
            raise ValueError(details)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_state(state: GameState) -> ValidationResult:
    """Check the invariants every system can rely on.

    This is intentionally structural rather than rules-specific.  A system's
    ``validate_action`` method adds the rules checks for a particular edition.
    """

    result = ValidationResult()

    if state.schema_version != SCHEMA_VERSION:
        result.add(
            "schema_version",
            f"expected schema version {SCHEMA_VERSION}, got {state.schema_version}",
            expected=SCHEMA_VERSION,
            actual=state.schema_version,
        )
    if not state.game_id:
        result.add("game_id", "game_id must not be empty")
    if not state.system_id:
        result.add("system_id", "system_id must not be empty")
    if state.round < 1:
        result.add("round", "round must be at least 1")
    if state.phase == "" and state.status == "active":
        result.add("phase", "an active game must have a current phase")
    if len(state.armies) < 2:
        result.add("armies", "a game needs at least two armies")

    seen_sides = set()
    seen_unit_ids = set()
    for army in state.armies:
        if army.side in seen_sides:
            result.add("duplicate_side", f"more than one army for side {army.side.value}")
        seen_sides.add(army.side)
        for unit in army.units:
            if unit.id in seen_unit_ids:
                result.add("duplicate_unit", f"duplicate unit id {unit.id!r}")
            seen_unit_ids.add(unit.id)
            if unit.side is not army.side:
                result.add(
                    "unit_side",
                    f"unit {unit.id!r} has side {unit.side.value}, "
                    f"but belongs to {army.side.value}",
                )
            if not state.board.contains(unit.position):
                result.add(
                    "unit_off_board",
                    f"unit {unit.id!r} is outside the board",
                    unit=unit.id,
                    position=unit.position.to_dict(),
                )
            if int(unit.wounds or 0) > unit.max_wounds:
                result.add(
                    "unit_wounds",
                    f"unit {unit.id!r} has more wounds than its maximum",
                    unit=unit.id,
                )
            if unit.destroyed and int(unit.wounds or 0) > 0:
                result.add(
                    "destroyed_wounds",
                    f"destroyed unit {unit.id!r} still has wounds",
                    unit=unit.id,
                )

    for feature in state.terrain:
        if not _polygon_on_board(feature.footprint, state):
            result.add(
                "terrain_off_board",
                f"terrain {feature.id!r} extends outside the board",
                terrain=feature.id,
            )
    for objective in state.objectives:
        if not state.board.contains(objective.position):
            result.add(
                "objective_off_board",
                f"objective {objective.id!r} is outside the board",
                objective=objective.id,
            )
        if objective.radius <= 0:
            result.add(
                "objective_radius",
                f"objective {objective.id!r} must have a positive radius",
                objective=objective.id,
            )

    for side, polygons in state.deployment_zones.items():
        try:
            Side.parse(side)
        except ValueError:
            result.add("deployment_side", f"unknown deployment zone side {side!r}")
        for index, polygon in enumerate(polygons):
            if not _polygon_on_board(polygon, state):
                result.add(
                    "deployment_off_board",
                    f"deployment zone {side}[{index}] extends outside the board",
                    side=side,
                    index=index,
                )

    for event_side in {event.side for event in state.events if event.side is not None}:
        try:
            Side.parse(event_side)
        except ValueError:
            result.add("event_side", f"event has unknown side {event_side!r}")

    if state.dice.cursor < 0:
        result.add("dice_cursor", "dice cursor must not be negative")

    for side in (Side.PLAYER, Side.AI):
        if state.scores.get(side.value, 0) < 0:
            result.add("score", f"{side.value} score must not be negative")
        if state.command_points.get(side.value, 0) < 0:
            result.add("command_points", f"{side.value} command points must not be negative")

    return result


def _polygon_on_board(polygon: Polygon, state: GameState) -> bool:
    return all(state.board.contains(point) for point in polygon.points)
