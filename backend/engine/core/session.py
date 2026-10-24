"""A thin orchestration layer around a system and its current state."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union

from backend.engine.core.events import Event
from backend.engine.core.models import GameState, Side
from backend.engine.core.serialization import (
    dumps_state,
    loads_state,
    save_state,
    state_from_dict,
)
from backend.engine.core.validation import ValidationResult, validate_state
from backend.engine.systems.base import (
    ActionResult,
    GameAction,
    GameSystem,
    IllegalActionError,
)


class GameSession:
    """Owns a system instance and the current immutable game state.

    Callers validate and apply actions through this class.  The state is
    replaced after each action; the previous object is never mutated.
    """

    def __init__(self, system: GameSystem, state: GameState) -> None:
        if state.system_id != system.system_id:
            raise ValueError(f"state is for system {state.system_id!r}, not {system.system_id!r}")
        self.system = system
        self._state = state

    @classmethod
    def new(cls, system: GameSystem, seed: int = 0, **options: Any) -> "GameSession":
        state = system.create_game(seed=seed, **options)
        session = cls(system, state)
        session.ensure_valid()
        return session

    @property
    def state(self) -> GameState:
        return self._state

    def legal_actions(self) -> List[GameAction]:
        return self.system.legal_actions(self._state)

    def validate(self, action: GameAction) -> ValidationResult:
        return self.system.validate_action(self._state, action)

    def apply(self, action: GameAction) -> List[Event]:
        validation = self.validate(action)
        if not validation.ok:
            raise IllegalActionError(
                f"illegal action {action.action_type}: {validation.errors[0].message}",
                validation,
            )
        before = self._state
        result: ActionResult = self.system.apply_action(before, action)
        next_state = result.state
        next_state.actions = list(next_state.actions)
        next_state.actions.append(action.to_dict())
        next_state.events = list(next_state.events)
        next_seq = max((event.seq for event in next_state.events), default=0) + 1
        stamped: List[Event] = []
        for event in result.events:
            event.seq = next_seq
            event.round = before.round
            event.phase = before.phase
            if event.side is None:
                event.side = before.active_side.value
            next_state.events.append(event)
            stamped.append(event)
            next_seq += 1
        self._state = next_state
        self.ensure_valid()
        return stamped

    def ensure_valid(self) -> None:
        result = validate_state(self._state)
        if not result.ok:
            details = "; ".join(issue.message for issue in result.errors)
            raise ValueError(f"invalid game state: {details}")

    def score(self, side: Side) -> int:
        return self.system.score(self._state, side)

    def is_terminal(self) -> bool:
        return self.system.is_terminal(self._state)

    def save(self, path: Union[str, Path]) -> Path:
        return save_state(self._state, path)

    def to_json(self, indent: int = 2) -> str:
        return dumps_state(self._state, indent=indent)

    def to_dict(self) -> Dict[str, Any]:
        return self._state.to_dict()

    @classmethod
    def from_json(cls, system: GameSystem, text: str) -> "GameSession":
        state = loads_state(text)
        return cls(system, state)

    @classmethod
    def from_dict(cls, system: GameSystem, payload: Dict[str, Any]) -> "GameSession":
        state = state_from_dict(payload)
        return cls(system, state)

    def summary(self) -> Dict[str, Any]:
        state = self._state
        return {
            "system": self.system.name,
            "round": state.round,
            "max_rounds": state.max_rounds,
            "active_side": state.active_side.value,
            "phase": state.phase,
            "status": state.status,
            "scores": dict(state.scores),
            "units": [
                {
                    "id": unit.id,
                    "name": unit.name,
                    "side": unit.side.value,
                    "models": unit.models,
                    "wounds": unit.wounds,
                    "position": unit.position.to_dict(),
                }
                for unit in state.all_units()
            ],
        }
