"""Roster parsing and starter rosters for the table companion.

Rosters are deliberately small: a name, a faction and a flat list of units.
There are no points, enhancements or matched-play rules. Validation checks only
that the profile is structurally usable, so a player can invent a unit for
their own table without fighting a list builder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

MAX_UNITS = 40
MAX_WEAPONS = 12
MAX_KEYWORDS = 24
MAX_NAME_LENGTH = 120
MAX_KEYWORD_LENGTH = 60
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class RosterParseError(ValueError):
    """Raised when a roster payload cannot be read as a playable roster."""

    def __init__(self, issues: Sequence[Mapping[str, str]]):
        self.issues: List[Dict[str, str]] = [dict(issue) for issue in issues]
        message = "; ".join(issue["message"] for issue in self.issues)
        super().__init__(message or "the roster is not valid")


@dataclass(frozen=True)
class TableWeapon:
    """A weapon profile as printed on a warscroll."""

    name: str
    range_inches: float
    attacks: int
    hit: int
    wound: int
    rend: int
    damage: int

    @property
    def is_ranged(self) -> bool:
        return self.range_inches > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "range": self.range_inches,
            "attacks": self.attacks,
            "hit": self.hit,
            "wound": self.wound,
            "rend": self.rend,
            "damage": self.damage,
        }


@dataclass(frozen=True)
class TableUnit:
    """One unit on the table, with only the fields the companion uses."""

    id: str
    name: str
    move: float
    save: int
    health: int
    models: int
    control: int
    keywords: Tuple[str, ...]
    weapons: Tuple[TableWeapon, ...]

    @property
    def is_hero(self) -> bool:
        return any(keyword.lower() == "hero" for keyword in self.keywords)

    @property
    def has_ranged_weapon(self) -> bool:
        return any(weapon.is_ranged for weapon in self.weapons)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "move": self.move,
            "save": self.save,
            "health": self.health,
            "models": self.models,
            "control": self.control,
            "keywords": list(self.keywords),
            "weapons": [weapon.to_dict() for weapon in self.weapons],
        }


@dataclass(frozen=True)
class Roster:
    """One side's list for the table."""

    name: str
    faction: str
    units: Tuple[TableUnit, ...]

    def unit(self, unit_id: str) -> Optional[TableUnit]:
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "faction": self.faction,
            "units": [unit.to_dict() for unit in self.units],
        }


def _issue(issues: List[Dict[str, str]], field: str, message: str) -> None:
    issues.append({"field": field, "message": message})


def _mapping(value: Any, context: str, issues: List[Dict[str, str]]) -> Optional[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        _issue(issues, context, f"{context} must be a JSON object")
        return None
    return value


def _text(
    payload: Mapping[str, Any],
    key: str,
    context: str,
    issues: List[Dict[str, str]],
    *,
    required: bool = True,
    default: str = "",
    maximum: int = MAX_NAME_LENGTH,
) -> str:
    value = payload.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            _issue(issues, f"{context}.{key}", f"{context}.{key} must be a non-empty string")
            return ""
        return default
    if not isinstance(value, str):
        _issue(issues, f"{context}.{key}", f"{context}.{key} must be a string")
        return default
    text = value.strip()
    if len(text) > maximum:
        _issue(
            issues,
            f"{context}.{key}",
            f"{context}.{key} must be at most {maximum} characters",
        )
        return text[:maximum]
    return text


def _number(
    payload: Mapping[str, Any],
    key: str,
    context: str,
    issues: List[Dict[str, str]],
    *,
    minimum: float = 0,
    default: Optional[float] = None,
) -> Optional[float]:
    value = payload.get(key)
    if value is None:
        if default is None:
            _issue(issues, f"{context}.{key}", f"{context}.{key} is required")
            return None
        return default
    if isinstance(value, bool):
        _issue(issues, f"{context}.{key}", f"{context}.{key} must be a number")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        _issue(issues, f"{context}.{key}", f"{context}.{key} must be a number")
        return None
    if number < minimum:
        _issue(
            issues,
            f"{context}.{key}",
            f"{context}.{key} must be at least {minimum:g}",
        )
        return None
    return number


def _integer(
    payload: Mapping[str, Any],
    key: str,
    context: str,
    issues: List[Dict[str, str]],
    *,
    minimum: int = 0,
    maximum: Optional[int] = None,
) -> Optional[int]:
    number = _number(payload, key, context, issues, minimum=minimum)
    if number is None:
        return None
    if int(number) != number:
        _issue(issues, f"{context}.{key}", f"{context}.{key} must be a whole number")
        return None
    result = int(number)
    if maximum is not None and result > maximum:
        _issue(
            issues,
            f"{context}.{key}",
            f"{context}.{key} must be at most {maximum}",
        )
        return None
    return result


def _keywords(
    payload: Mapping[str, Any],
    context: str,
    issues: List[Dict[str, str]],
) -> Tuple[str, ...]:
    raw = payload.get("keywords", [])
    if raw is None:
        return ()
    if not isinstance(raw, list):
        _issue(issues, f"{context}.keywords", f"{context}.keywords must be an array")
        return ()
    if len(raw) > MAX_KEYWORDS:
        _issue(
            issues,
            f"{context}.keywords",
            f"{context}.keywords may contain at most {MAX_KEYWORDS} entries",
        )
        raw = raw[:MAX_KEYWORDS]
    keywords: List[str] = []
    for index, value in enumerate(raw):
        if not isinstance(value, str) or not value.strip():
            _issue(
                issues,
                f"{context}.keywords[{index}]",
                f"{context}.keywords[{index}] must be a non-empty string",
            )
            continue
        keyword = value.strip()
        if len(keyword) > MAX_KEYWORD_LENGTH:
            _issue(
                issues,
                f"{context}.keywords[{index}]",
                f"{context}.keywords[{index}] must be at most {MAX_KEYWORD_LENGTH} characters",
            )
            continue
        keywords.append(keyword)
    return tuple(keywords)


def _parse_weapon(
    payload: Any,
    context: str,
    issues: List[Dict[str, str]],
) -> Optional[TableWeapon]:
    data = _mapping(payload, context, issues)
    if data is None:
        return None
    name = _text(data, "name", context, issues)
    range_inches = _number(data, "range", context, issues)
    attacks = _integer(data, "attacks", context, issues, minimum=1)
    hit = _integer(data, "hit", context, issues, minimum=2, maximum=6)
    wound = _integer(data, "wound", context, issues, minimum=2, maximum=6)
    rend = _integer(data, "rend", context, issues, minimum=0)
    damage = _integer(data, "damage", context, issues, minimum=1)
    if (
        range_inches is None
        or attacks is None
        or hit is None
        or wound is None
        or rend is None
        or damage is None
        or not name
    ):
        return None
    return TableWeapon(
        name=name,
        range_inches=float(range_inches),
        attacks=int(attacks),
        hit=int(hit),
        wound=int(wound),
        rend=int(rend),
        damage=int(damage),
    )


def _slug(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return slug or "unit"


def _unique_id(base: str, used: Iterable[str]) -> str:
    used_set = set(used)
    if base not in used_set:
        return base
    index = 2
    while f"{base}-{index}" in used_set:
        index += 1
    return f"{base}-{index}"


def _parse_unit(
    payload: Any,
    context: str,
    issues: List[Dict[str, str]],
    used_ids: List[str],
) -> Optional[TableUnit]:
    data = _mapping(payload, context, issues)
    if data is None:
        return None
    name = _text(data, "name", context, issues)
    move = _number(data, "move", context, issues)
    save = _integer(data, "save", context, issues, minimum=2, maximum=6)
    health = _integer(data, "health", context, issues, minimum=1)
    models = _integer(data, "models", context, issues, minimum=1)
    control = _integer(data, "control", context, issues, minimum=0)
    keywords = _keywords(data, context, issues)

    raw_weapons = data.get("weapons")
    weapons: List[TableWeapon] = []
    if not isinstance(raw_weapons, list) or not raw_weapons:
        _issue(issues, f"{context}.weapons", f"{context}.weapons must contain at least one weapon")
    elif len(raw_weapons) > MAX_WEAPONS:
        _issue(
            issues,
            f"{context}.weapons",
            f"{context}.weapons may contain at most {MAX_WEAPONS} weapons",
        )
    else:
        for index, raw_weapon in enumerate(raw_weapons):
            weapon = _parse_weapon(raw_weapon, f"{context}.weapons[{index}]", issues)
            if weapon is not None:
                weapons.append(weapon)

    if (
        move is None
        or save is None
        or health is None
        or models is None
        or control is None
        or not name
    ):
        return None
    if not weapons:
        return None

    raw_id = data.get("id")
    if raw_id is not None and not isinstance(raw_id, str):
        _issue(issues, f"{context}.id", f"{context}.id must be a string")
        raw_id = None
    base = _slug(raw_id) if raw_id and raw_id.strip() else _slug(name)
    unit_id = _unique_id(base, used_ids)
    used_ids.append(unit_id)

    return TableUnit(
        id=unit_id,
        name=name,
        move=float(move),
        save=int(save),
        health=int(health),
        models=int(models),
        control=int(control),
        keywords=keywords,
        weapons=tuple(weapons),
    )


def parse_roster(payload: Any) -> Roster:
    """Validate a JSON roster and return its canonical form.

    Unit IDs are derived from an explicit ``id`` when supplied, otherwise from
    the unit name.  Duplicate IDs are suffixed deterministically so a roster may
    legitimately contain two units with the same name.
    """

    issues: List[Dict[str, str]] = []
    data = _mapping(payload, "roster", issues)
    if data is None:
        raise RosterParseError(issues)

    name = _text(data, "name", "roster", issues, required=False, default="Custom roster")
    faction = _text(data, "faction", "roster", issues, required=False, default="")

    raw_units = data.get("units")
    units: List[TableUnit] = []
    if not isinstance(raw_units, list) or not raw_units:
        _issue(issues, "roster.units", "roster.units must contain at least one unit")
    elif len(raw_units) > MAX_UNITS:
        _issue(
            issues,
            "roster.units",
            f"roster.units may contain at most {MAX_UNITS} units",
        )
    else:
        used_ids: List[str] = []
        for index, raw_unit in enumerate(raw_units):
            unit = _parse_unit(raw_unit, f"roster.units[{index}]", issues, used_ids)
            if unit is not None:
                units.append(unit)

    if issues:
        raise RosterParseError(issues)

    return Roster(
        name=name or "Custom roster",
        faction=faction,
        units=tuple(units),
    )


def _starter_from_pack(pack_id: str) -> Roster:
    # Imported lazily so roster parsing stays usable without the data packs.
    from backend.engine.systems.aos4.datapack import load_faction_pack

    pack = load_faction_pack(pack_id)
    units = tuple(
        TableUnit(
            id=profile.id,
            name=profile.name,
            move=profile.move,
            save=profile.save,
            health=profile.health,
            models=profile.models,
            control=profile.control,
            keywords=profile.keywords,
            weapons=tuple(
                TableWeapon(
                    name=weapon.name,
                    range_inches=weapon.range_inches,
                    attacks=weapon.attacks,
                    hit=weapon.hit_on,
                    wound=weapon.wound_on,
                    rend=weapon.rend,
                    damage=weapon.damage,
                )
                for weapon in profile.weapons
            ),
        )
        for profile in pack.units
    )
    return Roster(name=pack.faction, faction=pack.faction, units=units)


def starter_rosters() -> Dict[str, Roster]:
    """The two preloaded rosters, keyed by their curated faction pack ID."""

    return {
        "stormcast-starter": _starter_from_pack("stormcast-starter"),
        "skaven-starter": _starter_from_pack("skaven-starter"),
    }


STARTER_DEFAULTS = {
    "player": "stormcast-starter",
    "ai": "skaven-starter",
}


__all__ = [
    "Roster",
    "RosterParseError",
    "STARTER_DEFAULTS",
    "TableUnit",
    "TableWeapon",
    "parse_roster",
    "starter_rosters",
]
