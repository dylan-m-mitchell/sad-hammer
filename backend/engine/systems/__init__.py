"""Rules modules that plug into the shared engine."""

from backend.engine.systems.base import (
    ActionResult,
    GameAction,
    GameSystem,
    IllegalActionError,
    PhaseDefinition,
)
from backend.engine.systems.demo import DemoSystem
from backend.engine.systems.registry import (
    UnknownSystemError,
    create_system,
    get_system_class,
    list_systems,
    register_system,
)

__all__ = [
    "ActionResult",
    "DemoSystem",
    "GameAction",
    "GameSystem",
    "IllegalActionError",
    "PhaseDefinition",
    "UnknownSystemError",
    "create_system",
    "get_system_class",
    "list_systems",
    "register_system",
]
