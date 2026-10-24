"""Pure combat helpers for Age of Sigmar 4th.

The resolver follows the core attack sequence: hit, wound, save, then a damage
pool.  Mortal damage from a critical hit skips the wound and save rolls, but
wards are still rolled for every point of damage.  Keeping this module free of
game-state mutation makes the probabilities easy to test and lets the AI reuse
exactly the same maths when it evaluates an attack.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from backend.engine.core.dice import Dice
from backend.engine.core.models import Unit, Weapon


def unit_edge_distance(first: Unit, second: Unit) -> float:
    """Distance between the two units' bases, never negative."""

    center = first.position.distance_to(second.position)
    return max(0.0, center - first.base_radius - second.base_radius)


def unit_in_combat(first: Unit, second: Unit, range_inches: float = 3.0) -> bool:
    if not first.alive or not second.alive:
        return False
    return unit_edge_distance(first, second) <= range_inches + 1e-9


def attack_hit(
    roll: int,
    hit_on: int,
    modifier: int = 0,
) -> bool:
    """Whether a natural hit roll succeeds under AoS modifiers.

    Unmodified 1s always fail; unmodified 6s are critical hits and count as
    hits.  Other rolls compare with the modified target number.
    """

    if roll == 1:
        return False
    if roll == 6:
        return True
    return roll + modifier >= hit_on


def save_succeeds(roll: int, save_target: int) -> bool:
    """Whether a save roll succeeds against an already-rend-modified target."""

    return roll != 1 and roll >= save_target


def ward_succeeds(roll: int, ward: int) -> bool:
    return roll >= ward


@dataclass
class AttackResult:
    attacks: int
    hits: int = 0
    critical_hits: int = 0
    wounds: int = 0
    saves: int = 0
    damage_pool: int = 0
    ward_saves: int = 0
    damage: int = 0
    log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attacks": self.attacks,
            "hits": self.hits,
            "critical_hits": self.critical_hits,
            "wounds": self.wounds,
            "saves": self.saves,
            "damage_pool": self.damage_pool,
            "ward_saves": self.ward_saves,
            "damage": self.damage,
            "attack_log": list(self.log),
        }


def resolve_weapon_attacks(
    dice: Dice,
    weapon: Weapon,
    target_save: int,
    target_ward: Optional[int],
    *,
    hit_modifier: int = 0,
    save_modifier: int = 0,
) -> AttackResult:
    """Roll one weapon's attacks and return the unsaved damage."""

    result = AttackResult(attacks=weapon.attacks)
    save_target = max(2, int(target_save) + int(weapon.armor_penetration) - int(save_modifier))
    crit_mortal = "crit_mortal" in weapon.keywords

    for _ in range(weapon.attacks):
        hit_roll = dice.d6()
        record: Dict[str, Any] = {
            "hit_roll": hit_roll,
            "hit_modifier": hit_modifier,
        }
        if not attack_hit(hit_roll, weapon.hit_on, hit_modifier):
            record["hit"] = False
            result.log.append(record)
            continue

        result.hits += 1
        critical = hit_roll == 6
        record["hit"] = True
        record["critical"] = critical
        if critical:
            result.critical_hits += 1

        if critical and crit_mortal:
            result.damage_pool += weapon.damage
            record["crit_mortal"] = True
            record["damage"] = weapon.damage
            result.log.append(record)
            continue

        wound_roll = dice.d6()
        record["wound_roll"] = wound_roll
        if wound_roll == 1 or wound_roll < weapon.wound_on:
            record["wound"] = False
            result.log.append(record)
            continue
        result.wounds += 1
        record["wound"] = True

        save_roll = dice.d6()
        record["save_roll"] = save_roll
        if save_succeeds(save_roll, save_target):
            result.saves += 1
            record["saved"] = True
            result.log.append(record)
            continue
        record["saved"] = False
        result.damage_pool += weapon.damage
        record["damage"] = weapon.damage
        result.log.append(record)

    for _ in range(result.damage_pool):
        if target_ward is None:
            result.damage += 1
            continue
        if ward_succeeds(dice.d6(), int(target_ward)):
            result.ward_saves += 1
        else:
            result.damage += 1

    return result


def _hit_probability(hit_on: int, modifier: int) -> float:
    return sum(1 for roll in range(1, 7) if attack_hit(roll, hit_on, modifier)) / 6.0


def _wound_probability(wound_on: int) -> float:
    return sum(1 for roll in range(1, 7) if roll != 1 and roll >= wound_on) / 6.0


def _save_failure_probability(save_target: int) -> float:
    return sum(1 for roll in range(1, 7) if not save_succeeds(roll, save_target)) / 6.0


def _ward_failure_probability(ward: Optional[int]) -> float:
    if ward is None:
        return 1.0
    return sum(1 for roll in range(1, 7) if not ward_succeeds(roll, int(ward))) / 6.0


def expected_damage(
    weapon: Weapon,
    target_save: int,
    target_ward: Optional[int],
    *,
    hit_modifier: int = 0,
    save_modifier: int = 0,
    attacks: Optional[int] = None,
) -> float:
    """Expected damage after hit, wound, save and ward rolls."""

    count = weapon.attacks if attacks is None else int(attacks)
    hit_chance = _hit_probability(weapon.hit_on, hit_modifier)
    crit_chance = 1.0 / 6.0
    wound_chance = _wound_probability(weapon.wound_on)
    save_target = max(2, int(target_save) + int(weapon.armor_penetration) - int(save_modifier))
    save_failure = _save_failure_probability(save_target)
    ward_failure = _ward_failure_probability(target_ward)
    crit_mortal = "crit_mortal" in weapon.keywords

    if crit_mortal:
        normal_hit_chance = max(0.0, hit_chance - crit_chance)
        expected = crit_chance * weapon.damage
        expected += normal_hit_chance * wound_chance * save_failure * weapon.damage
    else:
        expected = hit_chance * wound_chance * save_failure * weapon.damage
    return count * expected * ward_failure


def expected_weapon_damage(
    weapons: Sequence[Weapon],
    target_save: int,
    target_ward: Optional[int],
    *,
    hit_modifier: int = 0,
    save_modifier: int = 0,
    melee: Optional[bool] = None,
    ranged: Optional[bool] = None,
) -> float:
    total = 0.0
    for weapon in weapons:
        if melee is True and not weapon.is_melee:
            continue
        if ranged is True and weapon.is_melee:
            continue
        total += expected_damage(
            weapon,
            target_save,
            target_ward,
            hit_modifier=hit_modifier,
            save_modifier=save_modifier,
        )
    return total


def charge_probability(distance: float) -> float:
    """Probability that 2D6 reaches the required distance."""

    needed = int(math.ceil(max(0.0, float(distance)) - 1e-9))
    if needed <= 2:
        return 1.0
    if needed > 12:
        return 0.0
    outcomes = sum(1 for first in range(1, 7) for second in range(1, 7) if first + second >= needed)
    return outcomes / 36.0


__all__ = [
    "AttackResult",
    "attack_hit",
    "charge_probability",
    "expected_damage",
    "expected_weapon_damage",
    "resolve_weapon_attacks",
    "save_succeeds",
    "unit_edge_distance",
    "unit_in_combat",
    "ward_succeeds",
]
