"""Registry of available rules systems.

The registry is intentionally tiny: edition modules register themselves here,
and the API/CLI can list or instantiate a system without importing every module
at the call site.
"""

from __future__ import annotations

from typing import Dict, List, Type

from backend.engine.systems.aos4 import Aos4System
from backend.engine.systems.base import GameSystem
from backend.engine.systems.demo import DemoSystem


class UnknownSystemError(KeyError):
    """Raised when a requested system id is not registered."""


_SYSTEMS: Dict[str, Type[GameSystem]] = {
    Aos4System.system_id: Aos4System,
    DemoSystem.system_id: DemoSystem,
}


def get_system_class(system_id: str) -> Type[GameSystem]:
    key = str(system_id).strip().lower()
    try:
        return _SYSTEMS[key]
    except KeyError as exc:
        options = ", ".join(sorted(_SYSTEMS))
        raise UnknownSystemError(
            f"unknown system {system_id!r}; available systems: {options}"
        ) from exc


def create_system(system_id: str) -> GameSystem:
    return get_system_class(system_id)()


def list_systems() -> List[Dict[str, str]]:
    result = []
    for system_id in sorted(_SYSTEMS):
        system = _SYSTEMS[system_id]()
        result.append(
            {
                "id": system.system_id,
                "name": system.name,
                "edition": system.edition,
                "phases": ", ".join(phase.name for phase in system.phases),
            }
        )
    return result


def register_system(system: Type[GameSystem], *, replace: bool = False) -> None:
    """Register a rules module.

    Tests and future plugins can use this without editing the built-in map.
    """

    if not getattr(system, "system_id", ""):
        raise ValueError("system class must define system_id")
    key = system.system_id.strip().lower()
    if key in _SYSTEMS and not replace:
        raise ValueError(f"system {key!r} is already registered")
    _SYSTEMS[key] = system
