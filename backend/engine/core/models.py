"""System-agnostic game state and the objects that make up a battlefield."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple

from backend.engine.core.dice import DiceState
from backend.engine.core.events import Event
from backend.engine.core.geometry import Polygon, Vec2

SCHEMA_VERSION = 1


class Side(str, Enum):
    """The two players in a game."""

    PLAYER = "player"
    AI = "ai"

    @property
    def other(self) -> "Side":
        return Side.AI if self is Side.PLAYER else Side.PLAYER

    @classmethod
    def parse(cls, value: Any) -> "Side":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value))
        except ValueError as exc:
            raise ValueError(f"unknown side: {value!r}") from exc


@dataclass
class Board:
    """The physical tabletop, measured in inches."""

    width: float
    height: float
    name: str = "Battlefield"

    def __post_init__(self) -> None:
        self.width = float(self.width)
        self.height = float(self.height)
        if self.width <= 0 or self.height <= 0:
            raise ValueError("board dimensions must be positive")
        if not math.isfinite(self.width) or not math.isfinite(self.height):
            raise ValueError("board dimensions must be finite")

    def contains(self, point: Vec2, margin: float = 0.0) -> bool:
        """Return whether a point is on the board.

        A positive ``margin`` insets the playable area, which is useful for
        keeping a unit's whole base on the table.
        """

        margin = max(0.0, float(margin))
        return (
            margin <= point.x <= self.width - margin and margin <= point.y <= self.height - margin
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"width": self.width, "height": self.height, "name": self.name}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Board":
        return cls(
            width=float(payload["width"]),
            height=float(payload["height"]),
            name=str(payload.get("name", "Battlefield")),
        )


@dataclass
class Weapon:
    """A simple attack profile shared by the walking-skeleton systems.

    ``hit_on`` and ``wound_on`` are target numbers on a D6.  A system module may
    ignore these in favour of its own combat resolver, but keeping them explicit
    makes the demo and tests useful.
    """

    id: str
    name: str
    range_inches: float
    attacks: int
    hit_on: int
    wound_on: int
    damage: int = 1
    armor_penetration: int = 0
    keywords: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.range_inches = float(self.range_inches)
        self.attacks = int(self.attacks)
        self.hit_on = int(self.hit_on)
        self.wound_on = int(self.wound_on)
        self.damage = int(self.damage)
        self.armor_penetration = int(self.armor_penetration)
        if self.attacks < 1:
            raise ValueError("weapon attacks must be at least 1")
        if not 2 <= self.hit_on <= 6:
            raise ValueError("hit_on must be between 2 and 6")
        if not 2 <= self.wound_on <= 6:
            raise ValueError("wound_on must be between 2 and 6")
        if self.damage < 1:
            raise ValueError("damage must be at least 1")
        self.keywords = tuple(str(keyword) for keyword in self.keywords)

    @property
    def is_melee(self) -> bool:
        return self.range_inches <= 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "range_inches": self.range_inches,
            "attacks": self.attacks,
            "hit_on": self.hit_on,
            "wound_on": self.wound_on,
            "damage": self.damage,
            "armor_penetration": self.armor_penetration,
            "keywords": list(self.keywords),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Weapon":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            range_inches=float(payload["range_inches"]),
            attacks=int(payload["attacks"]),
            hit_on=int(payload["hit_on"]),
            wound_on=int(payload["wound_on"]),
            damage=int(payload.get("damage", 1)),
            armor_penetration=int(payload.get("armor_penetration", 0)),
            keywords=tuple(str(k) for k in payload.get("keywords", [])),
        )


@dataclass
class Unit:
    """A deployed unit in the digital twin.

    Multi-model units are represented by one centre point and a base radius for
    now.  The model-level footprint can grow later without changing this
    interface: systems already consume a unit ``id`` and a position.
    """

    id: str
    name: str
    side: Side
    position: Vec2
    weapons: List[Weapon] = field(default_factory=list)
    move: float = 5.0
    save: int = 4
    wounds_per_model: int = 1
    models: int = 1
    max_models: Optional[int] = None
    wounds: Optional[int] = None
    base_radius: float = 0.5
    keywords: Tuple[str, ...] = ()
    points: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)
    destroyed: bool = False

    def __post_init__(self) -> None:
        self.side = Side.parse(self.side)
        if not isinstance(self.position, Vec2):
            self.position = Vec2.from_dict(self.position)
        self.move = float(self.move)
        self.save = int(self.save)
        self.wounds_per_model = int(self.wounds_per_model)
        self.models = int(self.models)
        self.base_radius = float(self.base_radius)
        self.points = int(self.points)
        self.keywords = tuple(str(keyword) for keyword in self.keywords)
        if self.max_models is None:
            self.max_models = self.models
        self.max_models = int(self.max_models)
        if self.wounds is None:
            self.wounds = self.models * self.wounds_per_model
        self.wounds = int(self.wounds)
        if self.models < 0 or self.max_models < 0:
            raise ValueError("model counts must not be negative")
        if self.wounds_per_model < 1:
            raise ValueError("wounds_per_model must be at least 1")
        if self.wounds < 0:
            raise ValueError("wounds must not be negative")
        if self.wounds > self.max_models * self.wounds_per_model:
            raise ValueError("wounds exceed the unit's maximum")
        if self.move < 0:
            raise ValueError("move must not be negative")
        if self.base_radius <= 0:
            raise ValueError("base_radius must be positive")
        if not 2 <= self.save <= 6:
            raise ValueError("save must be between 2 and 6")
        if self.wounds == 0:
            self.models = 0
            self.destroyed = True
        elif self.models == 0:
            self.models = min(
                int(self.max_models or 0),
                max(1, math.ceil(int(self.wounds or 0) / self.wounds_per_model)),
            )
        self.weapons = [
            weapon if isinstance(weapon, Weapon) else Weapon.from_dict(weapon)
            for weapon in self.weapons
        ]

    @property
    def alive(self) -> bool:
        return not self.destroyed and int(self.wounds or 0) > 0 and self.models > 0

    @property
    def max_wounds(self) -> int:
        return int(self.max_models or 0) * self.wounds_per_model

    def weapon(self, weapon_id: str) -> Optional[Weapon]:
        for weapon in self.weapons:
            if weapon.id == weapon_id:
                return weapon
        return None

    def take_damage(self, amount: int) -> int:
        """Apply damage and return the amount actually removed."""

        if amount <= 0 or not self.alive:
            return 0
        before = int(self.wounds or 0)
        remaining = max(0, before - int(amount))
        self.wounds = remaining
        applied = before - remaining
        if remaining == 0:
            self.models = 0
            self.destroyed = True
        else:
            self.models = min(
                int(self.max_models or 0),
                max(1, math.ceil(remaining / self.wounds_per_model)),
            )
        return applied

    def reset_turn_flags(self) -> None:
        for key in ("moved", "advanced", "shot", "charged", "fought"):
            self.flags[key] = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "side": self.side.value,
            "position": self.position.to_dict(),
            "weapons": [weapon.to_dict() for weapon in self.weapons],
            "move": self.move,
            "save": self.save,
            "wounds_per_model": self.wounds_per_model,
            "models": self.models,
            "max_models": self.max_models,
            "wounds": self.wounds,
            "base_radius": self.base_radius,
            "keywords": list(self.keywords),
            "points": self.points,
            "stats": dict(self.stats),
            "flags": dict(self.flags),
            "destroyed": self.destroyed,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Unit":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            side=Side.parse(payload["side"]),
            position=Vec2.from_dict(payload["position"]),
            weapons=[Weapon.from_dict(item) for item in payload.get("weapons", [])],
            move=float(payload.get("move", 5.0)),
            save=int(payload.get("save", 4)),
            wounds_per_model=int(payload.get("wounds_per_model", 1)),
            models=int(payload.get("models", 1)),
            max_models=(
                int(payload["max_models"]) if payload.get("max_models") is not None else None
            ),
            wounds=int(payload["wounds"]) if payload.get("wounds") is not None else None,
            base_radius=float(payload.get("base_radius", 0.5)),
            keywords=tuple(str(k) for k in payload.get("keywords", [])),
            points=int(payload.get("points", 0)),
            stats=dict(payload.get("stats", {})),
            flags={str(k): bool(v) for k, v in payload.get("flags", {}).items()},
            destroyed=bool(payload.get("destroyed", False)),
        )


@dataclass
class Army:
    id: str
    name: str
    side: Side
    units: List[Unit] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.side = Side.parse(self.side)
        self.units = [
            unit if isinstance(unit, Unit) else Unit.from_dict(unit) for unit in self.units
        ]

    @property
    def alive_units(self) -> List[Unit]:
        return [unit for unit in self.units if unit.alive]

    def unit(self, unit_id: str) -> Optional[Unit]:
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "side": self.side.value,
            "units": [unit.to_dict() for unit in self.units],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Army":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            side=Side.parse(payload["side"]),
            units=[Unit.from_dict(item) for item in payload.get("units", [])],
        )


@dataclass
class TerrainFeature:
    id: str
    name: str
    footprint: Polygon
    height: float = 0.0
    cover: bool = False
    blocks_line_of_sight: bool = False
    difficult: bool = False
    tags: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.footprint, Polygon):
            self.footprint = Polygon.from_dict(self.footprint)
        self.height = float(self.height)
        self.tags = tuple(str(tag) for tag in self.tags)
        if self.height < 0:
            raise ValueError("terrain height must not be negative")

    def contains(self, point: Vec2) -> bool:
        return self.footprint.contains(point)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "footprint": self.footprint.to_dict(),
            "height": self.height,
            "cover": self.cover,
            "blocks_line_of_sight": self.blocks_line_of_sight,
            "difficult": self.difficult,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TerrainFeature":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            footprint=Polygon.from_dict(payload["footprint"]),
            height=float(payload.get("height", 0.0)),
            cover=bool(payload.get("cover", False)),
            blocks_line_of_sight=bool(payload.get("blocks_line_of_sight", False)),
            difficult=bool(payload.get("difficult", False)),
            tags=tuple(str(tag) for tag in payload.get("tags", [])),
        )


@dataclass
class Objective:
    id: str
    name: str
    position: Vec2
    radius: float = 3.0
    value: int = 1
    controller: Optional[Side] = None

    def __post_init__(self) -> None:
        if not isinstance(self.position, Vec2):
            self.position = Vec2.from_dict(self.position)
        self.radius = float(self.radius)
        self.value = int(self.value)
        if self.radius <= 0:
            raise ValueError("objective radius must be positive")
        if self.value < 0:
            raise ValueError("objective value must not be negative")
        if self.controller is not None:
            self.controller = Side.parse(self.controller)

    def contains(self, point: Vec2) -> bool:
        return self.position.distance_to(point) <= self.radius

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position.to_dict(),
            "radius": self.radius,
            "value": self.value,
            "controller": self.controller.value if self.controller else None,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Objective":
        controller = payload.get("controller")
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            position=Vec2.from_dict(payload["position"]),
            radius=float(payload.get("radius", 3.0)),
            value=int(payload.get("value", 1)),
            controller=Side.parse(controller) if controller is not None else None,
        )


@dataclass
class GameState:
    """The complete digital twin.

    The state is intentionally self-contained.  The API can remain stateless:
    the client can send this object with an action and receive a new version
    back.
    """

    system_id: str
    board: Board
    armies: List[Army]
    objectives: List[Objective] = field(default_factory=list)
    terrain: List[TerrainFeature] = field(default_factory=list)
    deployment_zones: Dict[str, List[Polygon]] = field(default_factory=dict)
    round: int = 1
    active_side: Side = Side.PLAYER
    phase: str = ""
    status: str = "active"
    scores: Dict[str, int] = field(default_factory=dict)
    command_points: Dict[str, int] = field(default_factory=dict)
    dice: DiceState = field(default_factory=lambda: DiceState(seed=0))
    actions: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    game_id: str = ""
    max_rounds: int = 5

    def __post_init__(self) -> None:
        if not isinstance(self.board, Board):
            self.board = Board.from_dict(self.board)
        self.active_side = Side.parse(self.active_side)
        self.armies = [
            army if isinstance(army, Army) else Army.from_dict(army) for army in self.armies
        ]
        self.objectives = [
            objective if isinstance(objective, Objective) else Objective.from_dict(objective)
            for objective in self.objectives
        ]
        self.terrain = [
            feature if isinstance(feature, TerrainFeature) else TerrainFeature.from_dict(feature)
            for feature in self.terrain
        ]
        self.deployment_zones = {
            str(Side.parse(side).value): [
                polygon if isinstance(polygon, Polygon) else Polygon.from_dict(polygon)
                for polygon in polygons
            ]
            for side, polygons in self.deployment_zones.items()
        }
        if not isinstance(self.dice, DiceState):
            self.dice = DiceState.from_dict(self.dice)
        self.actions = [dict(action) for action in self.actions]
        self.events = [
            event if isinstance(event, Event) else Event.from_dict(event) for event in self.events
        ]
        self.round = int(self.round)
        self.max_rounds = int(self.max_rounds)
        self.scores = {str(key): int(value) for key, value in self.scores.items()}
        self.command_points = {str(key): int(value) for key, value in self.command_points.items()}
        if self.round < 1:
            raise ValueError("round must be at least 1")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")
        if self.status not in ("active", "complete"):
            raise ValueError("status must be 'active' or 'complete'")

    @property
    def is_complete(self) -> bool:
        return self.status == "complete"

    def army_for(self, side: Side) -> Army:
        side = Side.parse(side)
        for army in self.armies:
            if army.side is side:
                return army
        raise KeyError(f"no army for side {side.value}")

    def enemy_side(self, side: Optional[Side] = None) -> Side:
        return Side.parse(side or self.active_side).other

    def all_units(self) -> List[Unit]:
        return [unit for army in self.armies for unit in army.units]

    def units_for(self, side: Side) -> List[Unit]:
        return list(self.army_for(side).units)

    def alive_units_for(self, side: Side) -> List[Unit]:
        return [unit for unit in self.units_for(side) if unit.alive]

    def unit_by_id(self, unit_id: str) -> Optional[Unit]:
        for army in self.armies:
            unit = army.unit(unit_id)
            if unit is not None:
                return unit
        return None

    def objective_by_id(self, objective_id: str) -> Optional[Objective]:
        for objective in self.objectives:
            if objective.id == objective_id:
                return objective
        return None

    def units_within(self, point: Vec2, radius: float) -> List[Unit]:
        return [
            unit
            for unit in self.all_units()
            if unit.alive and unit.position.distance_to(point) <= radius
        ]

    def score_for(self, side: Side) -> int:
        return int(self.scores.get(Side.parse(side).value, 0))

    def add_score(self, side: Side, amount: int) -> None:
        side = Side.parse(side)
        self.scores[side.value] = self.score_for(side) + int(amount)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "game_id": self.game_id,
            "system_id": self.system_id,
            "board": self.board.to_dict(),
            "armies": [army.to_dict() for army in self.armies],
            "objectives": [objective.to_dict() for objective in self.objectives],
            "terrain": [feature.to_dict() for feature in self.terrain],
            "deployment_zones": {
                side: [polygon.to_dict() for polygon in polygons]
                for side, polygons in self.deployment_zones.items()
            },
            "round": self.round,
            "max_rounds": self.max_rounds,
            "active_side": self.active_side.value,
            "phase": self.phase,
            "status": self.status,
            "scores": dict(self.scores),
            "command_points": dict(self.command_points),
            "dice": self.dice.to_dict(),
            "actions": [dict(action) for action in self.actions],
            "events": [event.to_dict() for event in self.events],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GameState":
        return cls(
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
            game_id=str(payload.get("game_id", "")),
            system_id=str(payload["system_id"]),
            board=Board.from_dict(payload["board"]),
            armies=[Army.from_dict(item) for item in payload.get("armies", [])],
            objectives=[Objective.from_dict(item) for item in payload.get("objectives", [])],
            terrain=[TerrainFeature.from_dict(item) for item in payload.get("terrain", [])],
            deployment_zones={
                str(side): [Polygon.from_dict(item) for item in polygons]
                for side, polygons in payload.get("deployment_zones", {}).items()
            },
            round=int(payload.get("round", 1)),
            max_rounds=int(payload.get("max_rounds", 5)),
            active_side=Side.parse(payload.get("active_side", Side.PLAYER.value)),
            phase=str(payload.get("phase", "")),
            status=str(payload.get("status", "active")),
            scores={str(key): int(value) for key, value in payload.get("scores", {}).items()},
            command_points={
                str(key): int(value) for key, value in payload.get("command_points", {}).items()
            },
            dice=DiceState.from_dict(payload.get("dice", {"seed": 0, "cursor": 0})),
            actions=[dict(item) for item in payload.get("actions", [])],
            events=[Event.from_dict(item) for item in payload.get("events", [])],
            metadata=dict(payload.get("metadata", {})),
        )
