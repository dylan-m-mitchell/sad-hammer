"""Versioned JSON serialization for complete game states."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Union

from backend.engine.core.models import SCHEMA_VERSION, GameState


class StateSerializationError(ValueError):
    """Raised when a saved state cannot be read safely."""


def state_to_dict(state: GameState) -> Dict[str, Any]:
    return state.to_dict()


def state_from_dict(payload: Mapping[str, Any]) -> GameState:
    if not isinstance(payload, Mapping):
        raise StateSerializationError("state payload must be an object")
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise StateSerializationError(
            f"unsupported state schema version {version!r}; expected {SCHEMA_VERSION}"
        )
    try:
        return GameState.from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise StateSerializationError(f"invalid game state: {exc}") from exc


def dumps_state(state: GameState, indent: int = 2) -> str:
    return json.dumps(state.to_dict(), indent=indent, sort_keys=True) + "\n"


def loads_state(text: str) -> GameState:
    if not isinstance(text, str):
        raise StateSerializationError("state JSON must be a string")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StateSerializationError(f"invalid JSON: {exc}") from exc
    return state_from_dict(payload)


def save_state(state: GameState, path: Union[str, os.PathLike[str]]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(dumps_state(state), encoding="utf-8")
    return destination


def load_state(path: Union[str, os.PathLike[str]]) -> GameState:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise StateSerializationError(f"could not read {source}: {exc}") from exc
    return loads_state(text)
