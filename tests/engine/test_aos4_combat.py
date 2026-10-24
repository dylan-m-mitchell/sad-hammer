from typing import List

import pytest

from backend.engine.core.geometry import Vec2
from backend.engine.core.models import Side, Unit, Weapon
from backend.engine.systems.aos4.combat import (
    attack_hit,
    charge_probability,
    expected_damage,
    expected_weapon_damage,
    resolve_weapon_attacks,
    save_succeeds,
    unit_edge_distance,
    unit_in_combat,
)


class FixedDice:
    def __init__(self, values: List[int]) -> None:
        self.values = list(values)

    def d6(self) -> int:
        if not self.values:
            raise AssertionError("the test ran out of fixed dice")
        return self.values.pop(0)


def _weapon(
    *,
    attacks: int = 1,
    hit_on: int = 3,
    wound_on: int = 3,
    rend: int = 0,
    damage: int = 1,
    crit_mortal: bool = False,
) -> Weapon:
    return Weapon(
        id="test-weapon",
        name="Test Weapon",
        range_inches=0,
        attacks=attacks,
        hit_on=hit_on,
        wound_on=wound_on,
        damage=damage,
        armor_penetration=rend,
        keywords=("crit_mortal",) if crit_mortal else (),
    )


def _unit(unit_id: str, position: Vec2, radius: float = 0.5) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        side=Side.PLAYER,
        position=position,
        base_radius=radius,
    )


def test_hit_and_save_helpers_follow_natural_one_and_six_rules():
    assert not attack_hit(1, 2, 5)
    assert attack_hit(6, 6, -1)
    assert attack_hit(3, 3, 0)
    assert not attack_hit(2, 3, 0)
    assert save_succeeds(6, 6)
    assert not save_succeeds(1, 2)
    assert not save_succeeds(3, 4)


def test_edge_distance_and_combat_range_use_bases():
    first = _unit("first", Vec2(0, 0), 1.0)
    second = _unit("second", Vec2(4, 0), 1.0)

    assert unit_edge_distance(first, second) == pytest.approx(2.0)
    assert unit_in_combat(first, second, 2.0)
    assert not unit_in_combat(first, second, 1.9)


def test_charge_probability_has_expected_2d6_curve():
    assert charge_probability(2) == 1.0
    assert charge_probability(7) == pytest.approx(21 / 36)
    assert charge_probability(12) == pytest.approx(1 / 36)
    assert charge_probability(13) == 0.0


def test_expected_damage_matches_the_full_sequence():
    weapon = _weapon(attacks=6, hit_on=3, wound_on=3)

    # 4/6 hit, 4/6 wound, 5/6 fail a 6+ save.
    assert expected_damage(weapon, 6, None) == pytest.approx(6 * (4 / 6) * (4 / 6) * (5 / 6))
    assert expected_weapon_damage([weapon], 6, None) == pytest.approx(
        expected_damage(weapon, 6, None)
    )


def test_critical_mortal_skips_save_but_not_ward():
    dice = FixedDice([6, 5, 4])
    result = resolve_weapon_attacks(
        dice,  # type: ignore[arg-type]
        _weapon(damage=2, crit_mortal=True),
        target_save=3,
        target_ward=5,
    )

    assert result.hits == 1
    assert result.critical_hits == 1
    assert result.wounds == 0
    assert result.saves == 0
    assert result.damage_pool == 2
    assert result.ward_saves == 1
    assert result.damage == 1
    assert result.log[0]["crit_mortal"] is True


def test_failed_save_and_ward_reduce_damage_per_point():
    dice = FixedDice([4, 3, 1, 5, 6])
    result = resolve_weapon_attacks(
        dice,  # type: ignore[arg-type]
        _weapon(damage=2, rend=1),
        target_save=3,
        target_ward=5,
    )

    assert result.wounds == 1
    assert result.saves == 0
    assert result.damage_pool == 2
    assert result.ward_saves == 2
    assert result.damage == 0


def test_successful_save_cancels_damage():
    dice = FixedDice([4, 3, 4])
    result = resolve_weapon_attacks(
        dice,  # type: ignore[arg-type]
        _weapon(damage=2, rend=1),
        target_save=3,
        target_ward=None,
    )

    assert result.wounds == 1
    assert result.saves == 1
    assert result.damage == 0


def test_missing_ward_is_not_confused_with_full_ward():
    dice = FixedDice([4, 3, 2])
    result = resolve_weapon_attacks(
        dice,  # type: ignore[arg-type]
        _weapon(damage=2, rend=1),
        target_save=3,
        target_ward=None,
    )

    assert result.damage == 2
    assert result.ward_saves == 0
