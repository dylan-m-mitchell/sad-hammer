import json

import pytest

from backend.engine.core.dice import DiceState
from backend.engine.core.geometry import Polygon, Vec2
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
from backend.engine.core.serialization import (
    StateSerializationError,
    dumps_state,
    loads_state,
    state_from_dict,
)
from backend.engine.core.validation import validate_state


def _weapon() -> Weapon:
    return Weapon(
        id="rifle",
        name="Rifle",
        range_inches=18,
        attacks=2,
        hit_on=4,
        wound_on=4,
        damage=1,
    )


def _state() -> GameState:
    player = Army(
        id="player",
        name="Player",
        side=Side.PLAYER,
        units=[
            Unit(
                id="p1",
                name="Player Unit",
                side=Side.PLAYER,
                position=Vec2(5, 5),
                weapons=[_weapon()],
                models=2,
                wounds_per_model=2,
            )
        ],
    )
    ai = Army(
        id="ai",
        name="AI",
        side=Side.AI,
        units=[
            Unit(
                id="a1",
                name="AI Unit",
                side=Side.AI,
                position=Vec2(15, 5),
                weapons=[_weapon()],
            )
        ],
    )
    return GameState(
        game_id="test-game",
        system_id="demo",
        board=Board(20, 10),
        armies=[player, ai],
        objectives=[Objective(id="o1", name="Objective", position=Vec2(10, 5))],
        terrain=[
            TerrainFeature(
                id="t1",
                name="Ruin",
                footprint=Polygon.rectangle(2, 2, 2, 2),
                cover=True,
            )
        ],
        deployment_zones={
            Side.PLAYER.value: [Polygon.rectangle(0, 0, 6, 10)],
            Side.AI.value: [Polygon.rectangle(14, 0, 6, 10)],
        },
        active_side=Side.PLAYER,
        phase="movement",
        dice=DiceState(seed=42),
    )


def test_unit_damage_updates_models_and_destruction():
    unit = Unit(
        id="u",
        name="Unit",
        side=Side.PLAYER,
        position=Vec2(0, 0),
        models=3,
        wounds_per_model=2,
    )

    assert unit.wounds == 6
    assert unit.take_damage(2) == 2
    assert unit.models == 2
    assert unit.take_damage(100) == 4
    assert unit.wounds == 0
    assert unit.models == 0
    assert unit.destroyed
    assert not unit.alive


def test_state_json_roundtrip_preserves_nested_objects():
    state = _state()
    encoded = dumps_state(state)
    decoded = loads_state(encoded)

    assert decoded.to_dict() == state.to_dict()
    assert json.loads(encoded)["schema_version"] == SCHEMA_VERSION
    assert decoded.armies[0].units[0].weapons[0].name == "Rifle"
    assert decoded.objectives[0].position == Vec2(10, 5)


def test_schema_version_is_required():
    payload = _state().to_dict()
    payload["schema_version"] = SCHEMA_VERSION + 1

    with pytest.raises(StateSerializationError):
        state_from_dict(payload)


def test_validation_accepts_valid_game_and_reports_off_board_unit():
    state = _state()
    assert validate_state(state).ok

    state.armies[0].units[0].position = Vec2(-1, 5)
    result = validate_state(state)

    assert not result.ok
    assert any(issue.code == "unit_off_board" for issue in result.errors)


def test_validation_reports_duplicate_unit_ids_and_wrong_sides():
    state = _state()
    state.armies[1].units.append(
        Unit(id="p1", name="Duplicate", side=Side.AI, position=Vec2(15, 6))
    )
    state.armies[1].units[0].side = Side.PLAYER

    result = validate_state(state)

    assert not result.ok
    codes = {issue.code for issue in result.errors}
    assert "duplicate_unit" in codes
    assert "unit_side" in codes
