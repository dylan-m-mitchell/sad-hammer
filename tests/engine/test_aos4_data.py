import json
from pathlib import Path

import pytest

from backend.engine.core.models import Side
from backend.engine.systems.aos4.datapack import (
    DataPackError,
    list_faction_packs,
    list_missions,
    load_faction_pack,
    load_mission,
)


def _raw_pack() -> dict:
    path = Path("data/aos4/factions/stormcast-starter.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_starter_packs_load_and_convert_to_units():
    stormcast = load_faction_pack("stormcast-starter")
    skaven = load_faction_pack("skaven-starter")

    assert stormcast.faction == "Stormcast Eternals"
    assert skaven.faction == "Skaven"
    assert len(stormcast.units) == 5
    assert len(skaven.units) == 6
    assert sum(unit.points for unit in stormcast.units) == 900
    assert sum(unit.points for unit in skaven.units) == 920

    profile = stormcast.unit("prosecutors")
    assert profile is not None
    unit = profile.to_unit(Side.PLAYER, profile_pos(), id_prefix="player")
    assert unit.id == "player-prosecutors"
    assert unit.stats["control"] == 1
    assert unit.keywords == ("Infantry", "Fly", "Stormcast Eternals", "Order")
    assert [weapon.id for weapon in unit.weapons] == [
        "stormcall-javelin",
        "celestial-hammer",
    ]
    assert unit.weapon("stormcall-javelin").range_inches == 12


def profile_pos():
    from backend.engine.core.geometry import Vec2

    return Vec2(10, 10)


def test_contested_ground_mission_has_expected_shape_and_safe_deployments():
    mission = load_mission("contested-ground")
    assert mission.board.width == 44
    assert mission.board.height == 30
    assert mission.rounds == 5
    assert len(mission.objectives) == 4
    assert mission.scoring["timing"] == "end_of_turn"
    assert [objective.id for objective in mission.objectives] == [
        "west-crossing",
        "north-cache",
        "south-cache",
        "east-crossing",
    ]
    assert len(mission.terrain) == 5

    for side, pack_name in (
        (Side.PLAYER, "stormcast-starter"),
        (Side.AI, "skaven-starter"),
    ):
        pack = load_faction_pack(pack_name)
        entries = mission.deployment_for(side, pack.pack_id)
        assert {entry.unit_id for entry in entries} == {unit.id for unit in pack.units}
        zone = mission.deployment_zones[side.value][0]
        positions = [entry.position for entry in entries]
        assert all(zone.contains(position) for position in positions)
        for index, position in enumerate(positions):
            for other in positions[index + 1 :]:
                assert position.distance_to(other) > 1.0


def test_lists_are_discoverable():
    assert "stormcast-starter" in list_faction_packs()
    assert "skaven-starter" in list_faction_packs()
    assert "contested-ground" in list_missions()


def test_pack_with_wrong_system_is_rejected(tmp_path):
    payload = _raw_pack()
    payload["system_id"] = "wh40k11"
    path = tmp_path / "wrong-system.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DataPackError, match="not 'aos4'"):
        load_faction_pack(path)


def test_pack_with_invalid_ward_and_duplicate_unit_is_rejected(tmp_path):
    payload = _raw_pack()
    payload["units"][0]["ward"] = 1
    bad_ward = tmp_path / "bad-ward.json"
    bad_ward.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DataPackError, match="ward"):
        load_faction_pack(bad_ward)

    payload = _raw_pack()
    payload["units"][1]["id"] = payload["units"][0]["id"]
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DataPackError, match="duplicate unit ids"):
        load_faction_pack(duplicate)


def test_missing_pack_has_actionable_error():
    with pytest.raises(DataPackError, match="available packs"):
        load_faction_pack("does-not-exist")
