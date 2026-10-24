"""The interface every rules system implements."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from backend.engine.core.geometry import Vec2
from backend.engine.core.models import GameState, Side
from backend.engine.core.validation import ValidationResult


class EngineError(Exception):
    """Base class for engine failures."""


class IllegalActionError(EngineError):
    """Raised when an action is not legal in the current state."""

    def __init__(self, message: str, validation: Optional[ValidationResult] = None) -> None:
        super().__init__(message)
        self.validation = validation


@dataclass(frozen=True)
class PhaseDefinition:
    id: str
    name: str
    description: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "name": self.name, "description": self.description}


@dataclass(frozen=True)
class GameAction:
    """A system-defined legal action.

    ``action_type`` is interpreted by the system.  The common fields cover
    movement, attacks and phase transitions without pretending that every
    edition uses the same verbs.
    """

    action_type: str
    actor_id: str
    target_id: Optional[str] = None
    destination: Optional[Vec2] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.action_type:
            raise ValueError("action_type must not be empty")
        if not self.actor_id:
            raise ValueError("actor_id must not be empty")
        if self.destination is not None and not isinstance(self.destination, Vec2):
            object.__setattr__(self, "destination", Vec2.from_dict(self.destination))
        object.__setattr__(self, "tags", tuple(str(tag) for tag in self.tags))

    def key(self) -> str:
        destination = (
            f"{self.destination.x:.4f},{self.destination.y:.4f}"
            if self.destination is not None
            else ""
        )
        payload = json.dumps(self.payload, sort_keys=True, separators=(",", ":"), default=str)
        return "|".join(
            [
                self.action_type,
                self.actor_id,
                self.target_id or "",
                destination,
                payload,
                ",".join(sorted(self.tags)),
            ]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "destination": self.destination.to_dict() if self.destination else None,
            "payload": dict(self.payload),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GameAction":
        destination = payload.get("destination")
        return cls(
            action_type=str(payload["action_type"]),
            actor_id=str(payload["actor_id"]),
            target_id=(str(payload["target_id"]) if payload.get("target_id") is not None else None),
            destination=Vec2.from_dict(destination) if destination is not None else None,
            payload=dict(payload.get("payload", {})),
            tags=tuple(str(tag) for tag in payload.get("tags", [])),
        )


@dataclass
class ActionResult:
    state: GameState
    events: List[Any] = field(default_factory=list)


class GameSystem(ABC):
    """A rules module plugged into the shared engine.

    Implementations must be deterministic: given the same state and action,
    ``apply_action`` must produce the same next state and events.  Randomness
    comes only from ``state.dice`` and must be written back to the returned
    state.
    """

    system_id: str = ""
    name: str = ""
    edition: str = ""

    @property
    @abstractmethod
    def phases(self) -> Sequence[PhaseDefinition]:
        """Phase order for one player's turn."""

    @abstractmethod
    def create_game(self, seed: int = 0, **options: Any) -> GameState:
        """Create a valid initial state."""

    @abstractmethod
    def legal_actions(self, state: GameState) -> List[GameAction]:
        """Enumerate legal actions for the active side."""

    @abstractmethod
    def validate_action(self, state: GameState, action: GameAction) -> ValidationResult:
        """Return every reason the action is not legal."""

    @abstractmethod
    def apply_action(self, state: GameState, action: GameAction) -> ActionResult:
        """Apply a validated action and return a new state plus events."""

    def phase(self, state: GameState) -> Optional[PhaseDefinition]:
        for phase in self.phases:
            if phase.id == state.phase:
                return phase
        return None

    def acting_side(self, state: GameState) -> Side:
        """Return the side that must choose the next action.

        Most phases belong to the active side.  Alternating combat is the
        exception: the active side can still be waiting while the other side
        picks a unit to fight, so clients and the AI must ask the system who is
        actually acting rather than assuming ``state.active_side``.
        """

        return state.active_side

    def action_side(self, state: GameState, action: GameAction) -> Side:
        """Return which side owns an action.

        Phase-level actions use a side name as their actor; unit actions use a
        unit id.  Falling back to the active side keeps custom systems working
        even when their phase actions use another convention.
        """

        unit = state.unit_by_id(action.actor_id)
        if unit is not None:
            return unit.side
        try:
            return Side.parse(action.actor_id)
        except ValueError:
            return state.active_side

    def legal_actions_for(self, state: GameState, side: Side) -> List[GameAction]:
        """Return only the legal actions owned by ``side``.

        This is the safe primitive for a human-vs-AI loop.  During alternating
        combat a system can enumerate fights for both sides in the same phase;
        an AI or a human client must never be allowed to choose the other
        side's units.
        """

        side = Side.parse(side)
        return [
            action
            for action in self.legal_actions(state)
            if self.action_side(state, action) is side
        ]

    def evaluate_action(
        self,
        state: GameState,
        action: GameAction,
        side: Side,
        weights: Optional[Mapping[str, float]] = None,
    ) -> float:
        """Heuristic value used by the utility AI.

        Systems should override this.  The default gives phase-ending a low
        value and no opinion about anything else, which is safe but not useful
        enough for a real opponent.
        """

        if action.action_type == "end_phase":
            return 0.0
        return 0.0

    def explain_action(self, state: GameState, action: GameAction, side: Side) -> str:
        """Return a short, human-readable reason for an AI decision."""

        return f"{side.value}: {action.action_type} with {action.actor_id}"

    def score(self, state: GameState, side: Side) -> int:
        return state.score_for(side)

    def is_terminal(self, state: GameState) -> bool:
        return state.status == "complete"

    def describe_state(self, state: GameState) -> str:
        return (
            f"{self.name}: round {state.round}, {state.active_side.value} "
            f"({state.phase}), {state.score_for(Side.PLAYER)}"
            f"-{state.score_for(Side.AI)}"
        )
