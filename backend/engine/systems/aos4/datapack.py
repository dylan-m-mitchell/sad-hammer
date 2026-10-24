"""Loading and validation for the curated Age of Sigmar 4th data packs.

The engine deliberately keeps rules code and unit data separate.  Data packs
are small, versioned JSON documents that can be replaced or extended without
changing the AoS module.  Nothing in this package downloads or stores
proprietary matched-play data; the starter packs are clearly sourced
approximations for the vertical slice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from backend.engine.core.geometry import Polygon, Vec2
from backend.engine.core.models import Board, Objective, Side, TerrainFeature, Unit, Weapon


class DataPackError(ValueError):
    """Raised when a data pack or mission cannot be loaded safely."""


def repo_root() -> Path:
    """Find the repository root without assuming the current directory."""

    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "backend").is_dir():
            return candidate
    raise DataPackError("could not find the repository root (no pyproject.toml found)")


def data_root() -> Path:
    return repo_root() / "data" / "aos4"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataPackError(f"could not read {path}: {exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataPackError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DataPackError(f"{path} must contain a JSON object")
    return payload


def _as_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DataPackError(f"{context} must be an object")
    return value


def _as_list(value: Any, context: str) -> List[Any]:
    if not isinstance(value, list):
        raise DataPackError(f"{context} must be an array")
    return value


def _string(
    payload: Mapping[str, Any],
    key: str,
    context: str,
    *,
    default: Optional[str] = None,
    required: bool = True,
) -> str:
    if key not in payload:
        if required:
            raise DataPackError(f"{context} is missing required field {key!r}")
        return default or ""
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise DataPackError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _number(
    payload: Mapping[str, Any],
    key: str,
    context: str,
    *,
    default: Optional[float] = None,
    required: bool = True,
) -> float:
    if key not in payload or payload[key] is None:
        if required:
            raise DataPackError(f"{context} is missing required field {key!r}")
        if default is None:
            raise DataPackError(f"{context}.{key} has no default")
        return float(default)
    try:
        value = float(payload[key])
    except (TypeError, ValueError) as exc:
        raise DataPackError(f"{context}.{key} must be a number") from exc
    if value < 0:
        raise DataPackError(f"{context}.{key} must not be negative")
    return value


def _integer(
    payload: Mapping[str, Any],
    key: str,
    context: str,
    *,
    default: Optional[int] = None,
    required: bool = True,
) -> int:
    if key not in payload or payload[key] is None:
        if required:
            raise DataPackError(f"{context} is missing required field {key!r}")
        if default is None:
            raise DataPackError(f"{context}.{key} has no default")
        return int(default)
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DataPackError(f"{context}.{key} must be an integer")
    if int(value) != value:
        raise DataPackError(f"{context}.{key} must be an integer")
    return int(value)


def _boolean(payload: Mapping[str, Any], key: str, context: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise DataPackError(f"{context}.{key} must be true or false")
    return value


def _keywords(payload: Mapping[str, Any], context: str) -> Tuple[str, ...]:
    raw = payload.get("keywords", [])
    values = _as_list(raw, f"{context}.keywords")
    result: List[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise DataPackError(f"{context}.keywords[{index}] must be a non-empty string")
        result.append(value.strip())
    return tuple(result)


@dataclass(frozen=True)
class WeaponProfile:
    id: str
    name: str
    range_inches: float
    attacks: int
    hit_on: int
    wound_on: int
    rend: int
    damage: int
    crit_mortal: bool = False

    def to_weapon(self) -> Weapon:
        keywords = ("crit_mortal",) if self.crit_mortal else ()
        return Weapon(
            id=self.id,
            name=self.name,
            range_inches=self.range_inches,
            attacks=self.attacks,
            hit_on=self.hit_on,
            wound_on=self.wound_on,
            damage=self.damage,
            armor_penetration=self.rend,
            keywords=keywords,
        )


@dataclass(frozen=True)
class UnitProfile:
    id: str
    name: str
    points: int
    move: float
    save: int
    health: int
    models: int
    control: int
    bravery: int
    ward: Optional[int]
    base_radius: float
    keywords: Tuple[str, ...]
    weapons: Tuple[WeaponProfile, ...]

    def to_unit(
        self,
        side: Side,
        position: Vec2,
        *,
        id_prefix: Optional[str] = None,
    ) -> Unit:
        unit_id = f"{id_prefix}-{self.id}" if id_prefix else self.id
        stats: Dict[str, Any] = {
            "control": self.control,
            "bravery": self.bravery,
            "ward": self.ward,
            "profile_id": self.id,
        }
        return Unit(
            id=unit_id,
            name=self.name,
            side=side,
            position=position,
            weapons=[weapon.to_weapon() for weapon in self.weapons],
            move=self.move,
            save=self.save,
            wounds_per_model=self.health,
            models=self.models,
            base_radius=self.base_radius,
            keywords=self.keywords,
            points=self.points,
            stats=stats,
            flags={},
        )


@dataclass(frozen=True)
class FactionPack:
    pack_id: str
    system_id: str
    edition: str
    faction: str
    source: str
    updated: str
    units: Tuple[UnitProfile, ...]

    def unit(self, unit_id: str) -> Optional[UnitProfile]:
        for profile in self.units:
            if profile.id == unit_id:
                return profile
        return None


@dataclass(frozen=True)
class DeploymentEntry:
    unit_id: str
    position: Vec2


@dataclass(frozen=True)
class Mission:
    mission_id: str
    name: str
    system_id: str
    edition: str
    source: str
    updated: str
    board: Board
    rounds: int
    deployment_zones: Dict[str, Tuple[Polygon, ...]]
    objectives: Tuple[Objective, ...]
    terrain: Tuple[TerrainFeature, ...]
    scoring: Dict[str, Any]
    deployment: Dict[str, Dict[str, Tuple[DeploymentEntry, ...]]]

    def deployment_for(self, side: Side, pack_id: str) -> Tuple[DeploymentEntry, ...]:
        side_key = Side.parse(side).value
        return self.deployment.get(side_key, {}).get(pack_id, ())

    def default_objectives(self) -> List[Objective]:
        return [
            Objective(
                id=objective.id,
                name=objective.name,
                position=objective.position,
                radius=objective.radius,
                value=objective.value,
            )
            for objective in self.objectives
        ]


def _parse_weapon(payload: Any, context: str) -> WeaponProfile:
    data = _as_mapping(payload, context)
    weapon_id = _string(data, "id", context)
    name = _string(data, "name", context)
    range_inches = _number(data, "range", context)
    attacks = _integer(data, "attacks", context)
    hit_on = _integer(data, "hit", context)
    wound_on = _integer(data, "wound", context)
    rend = _integer(data, "rend", context, default=0, required=False)
    damage = _integer(data, "damage", context)
    crit_mortal = _boolean(data, "crit_mortal", context, False)

    if attacks < 1:
        raise DataPackError(f"{context}.attacks must be at least 1")
    if not 2 <= hit_on <= 6:
        raise DataPackError(f"{context}.hit must be between 2 and 6")
    if not 2 <= wound_on <= 6:
        raise DataPackError(f"{context}.wound must be between 2 and 6")
    if rend < 0:
        raise DataPackError(f"{context}.rend must not be negative")
    if damage < 1:
        raise DataPackError(f"{context}.damage must be at least 1")

    return WeaponProfile(
        id=weapon_id,
        name=name,
        range_inches=range_inches,
        attacks=attacks,
        hit_on=hit_on,
        wound_on=wound_on,
        rend=rend,
        damage=damage,
        crit_mortal=crit_mortal,
    )


def _parse_unit(payload: Any, context: str) -> UnitProfile:
    data = _as_mapping(payload, context)
    unit_id = _string(data, "id", context)
    name = _string(data, "name", context)
    points = _integer(data, "points", context, default=0, required=False)
    move = _number(data, "move", context)
    save = _integer(data, "save", context)
    health = _integer(data, "health", context)
    models = _integer(data, "models", context, default=1, required=False)
    control = _integer(data, "control", context, default=1, required=False)
    bravery = _integer(data, "bravery", context, default=6, required=False)
    base_radius = _number(data, "base_radius", context, default=0.5, required=False)

    raw_ward = data.get("ward")
    if raw_ward is None:
        ward = None
    else:
        ward = _integer(data, "ward", context)
        if not 2 <= ward <= 6:
            raise DataPackError(f"{context}.ward must be between 2 and 6 or null")

    if save < 2 or save > 6:
        raise DataPackError(f"{context}.save must be between 2 and 6")
    if health < 1:
        raise DataPackError(f"{context}.health must be at least 1")
    if models < 1:
        raise DataPackError(f"{context}.models must be at least 1")
    if control < 0:
        raise DataPackError(f"{context}.control must not be negative")
    if base_radius <= 0:
        raise DataPackError(f"{context}.base_radius must be positive")

    raw_weapons = _as_list(data.get("weapons"), f"{context}.weapons")
    if not raw_weapons:
        raise DataPackError(f"{context}.weapons must contain at least one weapon")
    weapons = tuple(
        _parse_weapon(item, f"{context}.weapons[{index}]") for index, item in enumerate(raw_weapons)
    )
    weapon_ids = [weapon.id for weapon in weapons]
    if len(weapon_ids) != len(set(weapon_ids)):
        raise DataPackError(f"{context}.weapons contains duplicate weapon ids")

    return UnitProfile(
        id=unit_id,
        name=name,
        points=points,
        move=move,
        save=save,
        health=health,
        models=models,
        control=control,
        bravery=bravery,
        ward=ward,
        base_radius=base_radius,
        keywords=_keywords(data, context),
        weapons=weapons,
    )


def _faction_candidates(name: Union[str, Path]) -> List[Path]:
    requested = Path(name)
    candidates: List[Path] = []
    if requested.suffix.lower() == ".json":
        candidates.append(requested)
    else:
        candidates.append(requested.with_suffix(".json"))
    candidates.append(data_root() / "factions" / requested.name)
    if requested.suffix.lower() != ".json":
        candidates.append(data_root() / "factions" / f"{requested.name}.json")
    return candidates


def resolve_faction_path(name: Union[str, Path]) -> Path:
    for candidate in _faction_candidates(name):
        if candidate.is_file():
            return candidate
    options = ", ".join(sorted(path.stem for path in (data_root() / "factions").glob("*.json")))
    raise DataPackError(
        f"could not find faction pack {str(name)!r}; available packs: {options or 'none'}"
    )


def load_faction_pack(name: Union[str, Path]) -> FactionPack:
    path = resolve_faction_path(name)
    payload = _read_json(path)
    context = str(path)
    pack_id = _string(payload, "pack_id", context)
    system_id = _string(payload, "system_id", context)
    edition = _string(payload, "edition", context)
    faction = _string(payload, "faction", context)
    source = _string(payload, "source", context, default="", required=False)
    updated = _string(payload, "updated", context, default="", required=False)
    if system_id != "aos4":
        raise DataPackError(f"{context} is for system {system_id!r}, not 'aos4'")
    if str(edition).lower() not in ("4", "4th", "4.0"):
        raise DataPackError(f"{context}.edition must identify Age of Sigmar 4th")

    raw_units = _as_list(payload.get("units"), f"{context}.units")
    if not raw_units:
        raise DataPackError(f"{context}.units must contain at least one unit")
    units = tuple(
        _parse_unit(item, f"{context}.units[{index}]") for index, item in enumerate(raw_units)
    )
    unit_ids = [unit.id for unit in units]
    if len(unit_ids) != len(set(unit_ids)):
        raise DataPackError(f"{context}.units contains duplicate unit ids")

    return FactionPack(
        pack_id=pack_id,
        system_id=system_id,
        edition=edition,
        faction=faction,
        source=source,
        updated=updated,
        units=units,
    )


def _parse_polygon(payload: Any, context: str) -> Polygon:
    data = _as_mapping(payload, context)
    points: List[Vec2] = []
    raw_points = _as_list(data.get("points"), f"{context}.points")
    for index, raw_point in enumerate(raw_points):
        point = _as_mapping(raw_point, f"{context}.points[{index}]")
        try:
            points.append(Vec2(float(point["x"]), float(point["y"])))
        except (KeyError, TypeError, ValueError) as exc:
            raise DataPackError(f"{context}.points[{index}] must contain numeric x and y") from exc
    try:
        return Polygon(tuple(points))
    except ValueError as exc:
        raise DataPackError(f"{context} is invalid: {exc}") from exc


def _parse_terrain(payload: Any, context: str) -> TerrainFeature:
    data = _as_mapping(payload, context)
    footprint = _parse_polygon(data.get("footprint"), f"{context}.footprint")
    return TerrainFeature(
        id=_string(data, "id", context),
        name=_string(data, "name", context),
        footprint=footprint,
        height=_number(data, "height", context, default=0, required=False),
        cover=_boolean(data, "cover", context, False),
        blocks_line_of_sight=_boolean(data, "blocks_line_of_sight", context, False),
        difficult=_boolean(data, "difficult", context, False),
        tags=_keywords(data, context),
    )


def _parse_deployment(
    payload: Any,
    context: str,
    board: Board,
) -> Dict[str, Dict[str, Tuple[DeploymentEntry, ...]]]:
    if payload is None:
        return {}
    data = _as_mapping(payload, context)
    result: Dict[str, Dict[str, Tuple[DeploymentEntry, ...]]] = {}
    for side_key in ("player", "ai"):
        raw_side = data.get(side_key, {})
        side_map = _as_mapping(raw_side, f"{context}.{side_key}")
        result[side_key] = {}
        for pack_id, raw_entries in side_map.items():
            entries: List[DeploymentEntry] = []
            for index, raw_entry in enumerate(
                _as_list(raw_entries, f"{context}.{side_key}.{pack_id}")
            ):
                entry = _as_mapping(raw_entry, f"{context}.{side_key}.{pack_id}[{index}]")
                position_data = _as_mapping(
                    entry.get("position"), f"{context}.{side_key}.{pack_id}[{index}].position"
                )
                try:
                    position = Vec2(float(position_data["x"]), float(position_data["y"]))
                except (KeyError, TypeError, ValueError) as exc:
                    raise DataPackError(
                        f"{context}.{side_key}.{pack_id}[{index}].position "
                        "must contain numeric x and y"
                    ) from exc
                if not board.contains(position):
                    raise DataPackError(
                        f"{context} places {entry.get('unit_id')!r} outside the board"
                    )
                entries.append(
                    DeploymentEntry(
                        unit_id=_string(
                            entry,
                            "unit_id",
                            f"{context}.{side_key}.{pack_id}[{index}]",
                        ),
                        position=position,
                    )
                )
            result[side_key][pack_id] = tuple(entries)
    return result


def _mission_candidates(name: Union[str, Path]) -> List[Path]:
    requested = Path(name)
    candidates: List[Path] = []
    if requested.suffix.lower() == ".json":
        candidates.append(requested)
    else:
        candidates.append(requested.with_suffix(".json"))
    candidates.append(data_root() / "missions" / requested.name)
    if requested.suffix.lower() != ".json":
        candidates.append(data_root() / "missions" / f"{requested.name}.json")
    return candidates


def resolve_mission_path(name: Union[str, Path]) -> Path:
    for candidate in _mission_candidates(name):
        if candidate.is_file():
            return candidate
    options = ", ".join(sorted(path.stem for path in (data_root() / "missions").glob("*.json")))
    raise DataPackError(
        f"could not find mission {str(name)!r}; available missions: {options or 'none'}"
    )


def load_mission(name: Union[str, Path]) -> Mission:
    path = resolve_mission_path(name)
    payload = _read_json(path)
    context = str(path)
    system_id = _string(payload, "system_id", context)
    edition = _string(payload, "edition", context)
    if system_id != "aos4":
        raise DataPackError(f"{context} is for system {system_id!r}, not 'aos4'")
    if str(edition).lower() not in ("4", "4th", "4.0"):
        raise DataPackError(f"{context}.edition must identify Age of Sigmar 4th")

    board_data = _as_mapping(payload.get("board"), f"{context}.board")
    try:
        board = Board(
            width=float(board_data["width"]),
            height=float(board_data["height"]),
            name=str(board_data.get("name", "Battlefield")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DataPackError(f"{context}.board is invalid: {exc}") from exc

    rounds = _integer(payload, "rounds", context, default=5, required=False)
    if rounds < 1:
        raise DataPackError(f"{context}.rounds must be at least 1")

    raw_zones = _as_mapping(payload.get("deployment_zones"), f"{context}.deployment_zones")
    deployment_zones: Dict[str, Tuple[Polygon, ...]] = {}
    for side_key in ("player", "ai"):
        if side_key not in raw_zones:
            raise DataPackError(f"{context}.deployment_zones is missing {side_key!r}")
        polygons = tuple(
            _parse_polygon(item, f"{context}.deployment_zones.{side_key}[{index}]")
            for index, item in enumerate(
                _as_list(raw_zones[side_key], f"{context}.deployment_zones.{side_key}")
            )
        )
        if not polygons:
            raise DataPackError(f"{context}.deployment_zones.{side_key} must not be empty")
        for polygon in polygons:
            if not all(board.contains(point) for point in polygon.points):
                raise DataPackError(
                    f"{context}.deployment_zones.{side_key} extends outside the board"
                )
        deployment_zones[side_key] = polygons

    raw_objectives = _as_list(payload.get("objectives"), f"{context}.objectives")
    if not raw_objectives:
        raise DataPackError(f"{context}.objectives must contain at least one objective")
    objectives: List[Objective] = []
    for index, raw_objective in enumerate(raw_objectives):
        objective_context = f"{context}.objectives[{index}]"
        data = _as_mapping(raw_objective, objective_context)
        position_data = _as_mapping(data.get("position"), f"{objective_context}.position")
        try:
            position = Vec2(float(position_data["x"]), float(position_data["y"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise DataPackError(
                f"{objective_context}.position must contain numeric x and y"
            ) from exc
        if not board.contains(position):
            raise DataPackError(f"{objective_context} is outside the board")
        radius = _number(data, "radius", objective_context, default=3.0, required=False)
        if radius <= 0:
            raise DataPackError(f"{objective_context}.radius must be positive")
        objectives.append(
            Objective(
                id=_string(data, "id", objective_context),
                name=_string(data, "name", objective_context),
                position=position,
                radius=radius,
                value=_integer(data, "value", objective_context, default=1, required=False),
            )
        )
    objective_ids = [objective.id for objective in objectives]
    if len(objective_ids) != len(set(objective_ids)):
        raise DataPackError(f"{context}.objectives contains duplicate objective ids")

    raw_terrain = _as_list(payload.get("terrain", []), f"{context}.terrain")
    terrain = tuple(
        _parse_terrain(item, f"{context}.terrain[{index}]")
        for index, item in enumerate(raw_terrain)
    )
    for feature in terrain:
        if not all(board.contains(point) for point in feature.footprint.points):
            raise DataPackError(f"{context}.terrain {feature.id!r} extends outside the board")
    terrain_ids = [feature.id for feature in terrain]
    if len(terrain_ids) != len(set(terrain_ids)):
        raise DataPackError(f"{context}.terrain contains duplicate terrain ids")

    scoring_data = payload.get("scoring", {})
    if not isinstance(scoring_data, Mapping):
        raise DataPackError(f"{context}.scoring must be an object")
    scoring = dict(scoring_data)
    scoring.setdefault("timing", "end_of_turn")
    scoring.setdefault("points_per_objective", 1)
    scoring.setdefault("control_persists", True)

    deployment = _parse_deployment(payload.get("deployment"), f"{context}.deployment", board)

    return Mission(
        mission_id=_string(payload, "mission_id", context),
        name=_string(payload, "name", context),
        system_id=system_id,
        edition=edition,
        source=_string(payload, "source", context, default="", required=False),
        updated=_string(payload, "updated", context, default="", required=False),
        board=board,
        rounds=rounds,
        deployment_zones=deployment_zones,
        objectives=tuple(objectives),
        terrain=terrain,
        scoring=scoring,
        deployment=deployment,
    )


def list_faction_packs() -> List[str]:
    directory = data_root() / "factions"
    return sorted(path.stem for path in directory.glob("*.json"))


def list_missions() -> List[str]:
    directory = data_root() / "missions"
    return sorted(path.stem for path in directory.glob("*.json"))


__all__ = [
    "DataPackError",
    "DeploymentEntry",
    "FactionPack",
    "Mission",
    "UnitProfile",
    "WeaponProfile",
    "data_root",
    "list_faction_packs",
    "list_missions",
    "load_faction_pack",
    "load_mission",
    "repo_root",
    "resolve_faction_path",
    "resolve_mission_path",
]
