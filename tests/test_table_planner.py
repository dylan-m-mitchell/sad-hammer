"""Tests for the stateless table planner."""

from __future__ import annotations

import json
from typing import Iterable, Optional, Sequence

from backend.table.planner import (
    HOLD,
    PHASES,
    PRESS,
    SUPPORT,
    build_plan,
    choose_maneuver,
    classify_doctrine,
    support_movement_options,
)
from backend.table.rosters import Roster, TableUnit, TableWeapon


def weapon(
    name: str = "Blade",
    *,
    range_inches: float = 0,
    attacks: int = 2,
    damage: int = 1,
) -> TableWeapon:
    return TableWeapon(
        name=name,
        range_inches=range_inches,
        attacks=attacks,
        hit=3,
        wound=4,
        rend=0,
        damage=damage,
    )


def unit(
    unit_id: str,
    *,
    name: Optional[str] = None,
    keywords: Sequence[str] = ("Infantry",),
    weapons: Optional[Sequence[TableWeapon]] = None,
) -> TableUnit:
    return TableUnit(
        id=unit_id,
        name=name or unit_id.replace("-", " ").title(),
        move=5,
        save=4,
        health=2,
        models=1,
        control=1,
        keywords=tuple(keywords),
        weapons=tuple(weapons) if weapons is not None else (weapon(),),
    )


def roster(name: str, units: Iterable[TableUnit]) -> Roster:
    return Roster(name=name, faction=name, units=tuple(units))


def phases_by_id(plan: dict) -> dict:
    return {phase["id"]: phase for phase in plan["phases"]}


def instruction_for(plan: dict, phase: str, unit_id: str) -> dict:
    matches = [
        entry for entry in phases_by_id(plan)[phase]["instructions"] if entry["unit_id"] == unit_id
    ]
    assert matches, f"no {phase} instruction for {unit_id}"
    return matches[0]


def test_classify_melee_ranged_and_hero_units() -> None:
    assert classify_doctrine(unit("clanrats")) == PRESS
    assert classify_doctrine(unit("cannon", weapons=[weapon(range_inches=24)])) == SUPPORT
    assert (
        classify_doctrine(
            unit("seer", keywords=("Hero", "Wizard"), weapons=[weapon(range_inches=18)])
        )
        == HOLD
    )
    assert classify_doctrine(unit("guard", keywords=("Defensive",))) == HOLD
    assert (
        classify_doctrine(unit("mixed", weapons=[weapon(range_inches=12), weapon("Claw")]))
        == SUPPORT
    )


def test_plan_contains_the_six_phases_in_order() -> None:
    plan = build_plan(
        roster("You", [unit("liberators")]),
        roster("AI", [unit("clanrats")]),
        round_number=1,
        seed=7,
    )
    assert [phase["id"] for phase in plan["phases"]] == [phase for phase, _ in PHASES]
    assert [phase["name"] for phase in plan["phases"]] == [name for _, name in PHASES]


def test_instructions_use_relative_language_not_coordinates() -> None:
    plan = build_plan(
        roster("You", [unit("liberators")]),
        roster(
            "AI",
            [
                unit("clanrats"),
                unit("cannon", weapons=[weapon("Warp lightning", range_inches=24)]),
                unit("seer", keywords=("Hero",)),
            ],
        ),
        round_number=1,
        seed=3,
    )
    serialised = json.dumps(plan)
    assert '"position"' not in serialised
    assert '"coordinates"' not in serialised
    assert '"distance_inches"' not in serialised
    for phase in plan["phases"]:
        for entry in phase["instructions"]:
            if entry["unit_id"]:
                assert not any(
                    token in entry["instruction"].lower() for token in (" x ", " y ", "coordinates")
                )


def test_support_units_never_default_to_a_charge() -> None:
    plan = build_plan(
        roster("You", [unit("liberators")]),
        roster("AI", [unit("cannon", weapons=[weapon(range_inches=24)])]),
        round_number=1,
        seed=5,
    )
    charge = instruction_for(plan, "charge", "cannon")
    assert charge["maneuver"] == "no_charge"
    assert "do not charge" in charge["instruction"].lower()
    assert "within 6 inches" in charge["instruction"].lower()
    assert "no shooting target" in charge["instruction"].lower()
    assert instruction_for(plan, "shooting", "cannon")["maneuver"] != "charge"


def test_support_shooting_uses_only_ranged_weapons() -> None:
    plan = build_plan(
        roster("You", [unit("liberators")]),
        roster(
            "AI",
            [
                unit(
                    "prosecutors",
                    weapons=[
                        weapon("Javelin", range_inches=12),
                        weapon("Celestial hammer"),
                    ],
                )
            ],
        ),
        round_number=2,
        seed=5,
    )
    shooting = instruction_for(plan, "shooting", "prosecutors")
    assert [profile["name"] for profile in shooting["weapons"]] == ["Javelin"]
    combat = instruction_for(plan, "combat", "prosecutors")
    assert [profile["name"] for profile in combat["weapons"]] == ["Celestial hammer"]


def test_press_units_do_not_get_a_shooting_instruction() -> None:
    plan = build_plan(
        roster("You", [unit("liberators")]),
        roster("AI", [unit("clanrats")]),
        round_number=1,
        seed=5,
    )
    assert phases_by_id(plan)["shooting"]["instructions"] == []
    assert instruction_for(plan, "combat", "clanrats")["maneuver"] == "fight"


def test_hero_phase_only_contains_hold_units() -> None:
    plan = build_plan(
        roster("You", [unit("liberators")]),
        roster(
            "AI",
            [
                unit("clanrats"),
                unit("cannon", weapons=[weapon(range_inches=24)]),
                unit("seer", keywords=("Hero",)),
            ],
        ),
        round_number=1,
        seed=9,
    )
    hero_units = [entry["unit_id"] for entry in phases_by_id(plan)["hero"]["instructions"]]
    assert hero_units == ["seer"]


def test_defensive_units_hold_without_a_hero_phase_action() -> None:
    plan = build_plan(
        roster("You", [unit("liberators")]),
        roster("AI", [unit("guard", keywords=("Defensive",))]),
        round_number=1,
        seed=9,
    )
    assert phases_by_id(plan)["hero"]["instructions"] == []
    assert instruction_for(plan, "movement", "guard")["doctrine"] == HOLD


def test_plan_is_deterministic_for_the_same_round_and_seed() -> None:
    player = roster("You", [unit("liberators")])
    ai = roster(
        "AI",
        [
            unit("clanrats"),
            unit("cannon", weapons=[weapon(range_inches=24)]),
            unit("seer", keywords=("Hero",)),
        ],
    )
    first = build_plan(player, ai, round_number=3, seed=123)
    second = build_plan(player, ai, round_number=3, seed=123)
    assert first == second


def test_maneuvers_rotate_from_round_to_round() -> None:
    player = roster("You", [unit("liberators")])
    ai = roster("AI", [unit("clanrats")])
    maneuvers = [
        instruction_for(
            build_plan(player, ai, round_number=round_number, seed=11),
            "movement",
            "clanrats",
        )["maneuver"]
        for round_number in (1, 2, 3)
    ]
    assert len(set(maneuvers)) == 3


def test_seed_chooses_different_maneuvers() -> None:
    options = support_movement_options(["Enemy Hero"])
    chosen = {
        choose_maneuver(
            options,
            seed=seed,
            unit_id="cannon",
            phase="movement",
            round_number=1,
        ).id
        for seed in range(12)
    }
    assert len(chosen) > 1


def test_focus_hero_requires_an_enemy_hero() -> None:
    without_hero = support_movement_options([])
    with_hero = support_movement_options(["Grey Seer"])
    assert "focus_hero" not in {maneuver.id for maneuver in without_hero}
    assert "focus_hero" in {maneuver.id for maneuver in with_hero}

    moves = {
        instruction_for(
            build_plan(
                roster("You", [unit("seer", keywords=("Hero",))]),
                roster("AI", [unit("cannon", weapons=[weapon(range_inches=24)])]),
                round_number=round_number,
                seed=4,
            ),
            "movement",
            "cannon",
        )["maneuver"]
        for round_number in (1, 2, 3, 4)
    }
    assert "focus_hero" in moves
    for round_number in (1, 2, 3, 4):
        candidate = build_plan(
            roster("You", [unit("seer", keywords=("Hero",))]),
            roster("AI", [unit("cannon", weapons=[weapon(range_inches=24)])]),
            round_number=round_number,
            seed=4,
        )
        shooting = instruction_for(candidate, "shooting", "cannon")
        if shooting["maneuver"] == "focus_hero":
            assert "enemy hero" in shooting["instruction"].lower()


def test_destroyed_units_are_filtered_out_of_every_phase() -> None:
    player = roster("You", [unit("liberators")])
    ai = roster("AI", [unit("clanrats"), unit("rat-ogors")])
    plan = build_plan(player, ai, round_number=1, seed=2, destroyed=["clanrats", "unknown-unit"])
    assert [entry["id"] for entry in plan["units"]] == ["rat-ogors"]
    assert plan["ai_roster"]["destroyed"] == ["clanrats"]
    assert plan["ai_roster"]["active_count"] == 1
    for phase in plan["phases"]:
        assert all(entry["unit_id"] != "clanrats" for entry in phase["instructions"])
    assert any(
        entry["unit_id"] == "rat-ogors" for entry in phases_by_id(plan)["movement"]["instructions"]
    )


def test_destroyed_units_can_be_marked_by_name() -> None:
    ai = roster("AI", [unit("clanrats", name="Clanrats")])
    plan = build_plan(
        roster("You", [unit("liberators")]),
        ai,
        round_number=1,
        seed=2,
        destroyed=["Clanrats"],
    )
    assert plan["units"] == []
    assert plan["ai_roster"]["destroyed"] == ["clanrats"]


def test_end_phase_is_always_present_and_general() -> None:
    ai = roster("AI", [unit("clanrats")])
    plan = build_plan(
        roster("You", [unit("liberators")]),
        ai,
        round_number=1,
        seed=2,
        destroyed=["clanrats"],
    )
    end_phase = phases_by_id(plan)["end"]
    assert len(end_phase["instructions"]) == 2
    assert all(entry["unit_id"] is None for entry in end_phase["instructions"])
    assert any("objective" in entry["instruction"].lower() for entry in end_phase["instructions"])
