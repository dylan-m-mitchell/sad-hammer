import json
from pathlib import Path

import pytest

from backend.engine.core.models import Side
from backend.engine.systems.aos4.datapack import (
    DataPackError,
    list_faction_packs,
    list_missions,
    load_faction_pack,
    load_faction_pack_file,
    load_mission,
    load_mission_file,
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
        load_faction_pack_file(path)


def test_pack_with_invalid_ward_and_duplicate_unit_is_rejected(tmp_path):
    payload = _raw_pack()
    payload["units"][0]["ward"] = 1
    bad_ward = tmp_path / "bad-ward.json"
    bad_ward.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DataPackError, match="ward"):
        load_faction_pack_file(bad_ward)

    payload = _raw_pack()
    payload["units"][1]["id"] = payload["units"][0]["id"]
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DataPackError, match="duplicate unit ids"):
        load_faction_pack_file(duplicate)


def test_missing_pack_has_actionable_error():
    with pytest.raises(DataPackError, match="available packs"):
        load_faction_pack("does-not-exist")


@pytest.mark.parametrize(
    "load_id,load_file,relative_path",
    [
        (load_faction_pack, load_faction_pack_file, "factions/stormcast-starter.json"),
        (load_mission, load_mission_file, "missions/contested-ground.json"),
    ],
)
def test_curated_loaders_reject_paths_and_ignore_working_directory(
    tmp_path, monkeypatch, load_id, load_file, relative_path
):
    source = Path("data/aos4", relative_path).resolve()
    external = tmp_path / source.name
    external.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    assert load_file(external) == load_id(source.stem)

    for value in (
        str(external),
        external,
        f"../{source.stem}",
        f"nested/{source.stem}",
        f"nested\\{source.stem}",
        source.name,
    ):
        with pytest.raises(DataPackError, match="bare curated data ID"):
            load_id(value)

    # A valid ID must resolve from curated data even if the CWD has a namesake.
    external.write_text("{}", encoding="utf-8")
    expected = load_id(source.stem)
    monkeypatch.chdir(tmp_path)
    assert load_id(source.stem) == expected


@pytest.mark.parametrize(
    "load_id,directory", [(load_faction_pack, "factions"), (load_mission, "missions")]
)
def test_curated_loaders_reject_symlinks_outside_data_directory(
    tmp_path, monkeypatch, load_id, directory
):
    root = tmp_path / "curated"
    curated = root / directory
    curated.mkdir(parents=True)
    external = tmp_path / "external.json"
    external.write_text("{}", encoding="utf-8")
    (curated / "escape.json").symlink_to(external)
    monkeypatch.setattr("backend.engine.systems.aos4.datapack.data_root", lambda: root)

    with pytest.raises(DataPackError, match="inside its data directory"):
        load_id("escape")
