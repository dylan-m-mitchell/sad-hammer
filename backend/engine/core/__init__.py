"""Shared, system-agnostic engine primitives."""

from backend.engine.core.dice import Dice, DiceError, DiceRoll, DiceState
from backend.engine.core.events import Event
from backend.engine.core.geometry import Polygon, Rect, Vec2
from backend.engine.core.models import (
    SCHEMA_VERSION,
    Army,
    Board,
    GameState,
    Objective,
    Side,
    TerrainFeature,
    Unit,
    Weapon,
)

__all__ = [
    "SCHEMA_VERSION",
    "Army",
    "Board",
    "Dice",
    "DiceError",
    "DiceRoll",
    "DiceState",
    "Event",
    "GameState",
    "Objective",
    "Polygon",
    "Rect",
    "Side",
    "TerrainFeature",
    "Unit",
    "Vec2",
    "Weapon",
]
