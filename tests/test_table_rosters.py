"""Tests for table roster parsing and the preloaded starter rosters."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from backend.table.rosters import (
    RosterParseError,
    parse_roster,
    starter_rosters,
)


def weapon(**overrides: Any) -> Dict[str, Any]:
    data = {
        "name": "Blade",
        "range": 0,
        "attacks": 2,
        "hit": 3,
        "wound": 4,
        "rend": 0,
        "damage": 1,
    }
    data.update(overrides)
    return data


def unit(**overrides: Any) -> Dict[str, Any]:
    data = {
        "name": "Test Unit",
        "move": 5,
        "save": 4,
        "health": 2,
        "models": 1,
        "control": 1,
        "keywords": ["Infantry"],
        "weapons": [weapon()],
    }
    data.update(overrides)
    return data


def roster(**overrides: Any) -> Dict[str, Any]:
    data = {
        "name": "My roster",
        "faction": "Order",
        "units": [unit()],
    }
    data.update(overrides)
    return data


def test_minimal_roster_is_canonicalised() -> None:
    parsed = parse_roster(roster())
    assert parsed.name == "My roster"
    assert parsed.faction == "Order"
    assert len(parsed.units) == 1
    parsed_unit = parsed.units[0]
    assert parsed_unit.id == "test-unit"
    assert parsed_unit.name == "Test Unit"
    assert parsed_unit.move == 5
    assert parsed_unit.weapons[0].name == "Blade"
    assert parsed_unit.weapons[0].range_inches == 0
    assert parsed_unit.weapons[0].attacks == 2
    assert parsed_unit.to_dict()["weapons"][0] == {
        "name": "Blade",
        "range": 0,
        "attacks": 2,
        "hit": 3,
        "wound": 4,
        "rend": 0,
        "damage": 1,
    }


def test_numeric_strings_are_accepted_for_easy_json_import() -> None:
    parsed = parse_roster(
        roster(units=[unit(move="5", save="3", health="3", models="5", control="2")])
    )
    parsed_unit = parsed.units[0]
    assert parsed_unit.move == 5
    assert parsed_unit.save == 3
    assert parsed_unit.health == 3
    assert parsed_unit.models == 5
    assert parsed_unit.control == 2


def test_explicit_unit_id_is_used_and_duplicates_are_suffixed() -> None:
    parsed = parse_roster(
        roster(
            units=[
                unit(name="Clanrats", id="clanrats"),
                unit(name="Clanrats"),
                unit(name="Clanrats"),
            ]
        )
    )
    assert [entry.id for entry in parsed.units] == [
        "clanrats",
        "clanrats-2",
        "clanrats-3",
    ]


def test_missing_optional_name_and_faction_get_defaults() -> None:
    parsed = parse_roster({"units": [unit()]})
    assert parsed.name == "Custom roster"
    assert parsed.faction == ""


def test_unknown_fields_such_as_points_are_ignored() -> None:
    parsed = parse_roster(roster(units=[unit(points=250, role="Battleline")]))
    assert "points" not in parsed.units[0].to_dict()


def test_roster_requires_at_least_one_unit() -> None:
    with pytest.raises(RosterParseError) as error:
        parse_roster(roster(units=[]))
    assert error.value.issues[0]["field"] == "roster.units"


def test_unit_requires_a_weapon() -> None:
    with pytest.raises(RosterParseError) as error:
        parse_roster(roster(units=[unit(weapons=[])]))
    assert any(issue["field"] == "roster.units[0].weapons" for issue in error.value.issues)


@pytest.mark.parametrize(
    "broken,field",
    [
        (unit(save=1), "roster.units[0].save"),
        (unit(save=7), "roster.units[0].save"),
        (unit(health=0), "roster.units[0].health"),
        (unit(models=0), "roster.units[0].models"),
        (unit(control=-1), "roster.units[0].control"),
        (unit(move="fast"), "roster.units[0].move"),
        (unit(name=""), "roster.units[0].name"),
        (unit(weapons=[weapon(range=-1)]), "roster.units[0].weapons[0].range"),
        (unit(weapons=[weapon(attacks=0)]), "roster.units[0].weapons[0].attacks"),
        (unit(weapons=[weapon(hit=7)]), "roster.units[0].weapons[0].hit"),
        (unit(weapons=[weapon(damage=0)]), "roster.units[0].weapons[0].damage"),
    ],
)
def test_invalid_profiles_report_their_field(broken: Dict[str, Any], field: str) -> None:
    with pytest.raises(RosterParseError) as error:
        parse_roster(roster(units=[broken]))
    assert any(issue["field"] == field for issue in error.value.issues)


@pytest.mark.parametrize("value", ["nan", "inf", 10**400])
def test_non_finite_numbers_report_their_field(value: Any) -> None:
    with pytest.raises(RosterParseError) as error:
        parse_roster(roster(units=[unit(move=value)]))
    assert any(issue["field"] == "roster.units[0].move" for issue in error.value.issues)


def test_keywords_must_be_strings() -> None:
    with pytest.raises(RosterParseError) as error:
        parse_roster(roster(units=[unit(keywords=["Hero", 7])]))
    assert error.value.issues[0]["field"] == "roster.units[0].keywords[1]"


def test_starter_rosters_are_playable_profiles() -> None:
    starters = starter_rosters()
    assert set(starters) == {"stormcast-starter", "skaven-starter"}
    stormcast = starters["stormcast-starter"]
    skaven = starters["skaven-starter"]
    assert stormcast.name == "Stormcast Eternals"
    assert skaven.name == "Skaven"
    assert len(stormcast.units) == 5
    assert len(skaven.units) == 6

    prosecutors = next(unit for unit in stormcast.units if unit.name == "Prosecutors")
    assert prosecutors.id == "prosecutors"
    assert any(weapon.is_ranged for weapon in prosecutors.weapons)
    assert any(not weapon.is_ranged for weapon in prosecutors.weapons)

    grey_seer = next(unit for unit in skaven.units if unit.name == "Grey Seer")
    assert grey_seer.is_hero
    assert "Wizard" in grey_seer.keywords

    for entry in (stormcast, skaven):
        for starter_unit in entry.units:
            assert starter_unit.weapons
            assert starter_unit.health >= 1
            assert starter_unit.models >= 1
            assert 2 <= starter_unit.save <= 6
