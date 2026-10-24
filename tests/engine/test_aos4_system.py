from typing import Optional

import pytest

from backend.engine.ai.policy import PROFILES, UtilityAI, get_profile, run_ai_turn
from backend.engine.core.geometry import Vec2
from backend.engine.core.models import Side
from backend.engine.core.session import GameSession
from backend.engine.systems.aos4 import Aos4System
from backend.engine.systems.base import GameAction, IllegalActionError


def _session(seed: int = 1, max_rounds: int = 1) -> GameSession:
    return GameSession.new(
        Aos4System(),
        seed=seed,
        max_rounds=max_rounds,
        skip_deployment=True,
    )


def _find(
    session: GameSession,
    action_type: str,
    *,
    actor_id: Optional[str] = None,
    target_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> GameAction:
    for action in session.legal_actions():
        if action.action_type != action_type:
            continue
        if actor_id is not None and action.actor_id != actor_id:
            continue
        if target_id is not None and action.target_id != target_id:
            continue
        if payload is not None and any(
            action.payload.get(key) != value for key, value in payload.items()
        ):
            continue
        return action
    raise AssertionError(f"no {action_type} action for actor={actor_id!r}, target={target_id!r}")


def _set_phase(session: GameSession, phase: str) -> None:
    session.state.phase = phase
    session.state.metadata["combat_last_side"] = None
    session.state.metadata["command_usage"] = {}


def _end_phase(session: GameSession) -> None:
    session.apply(_find(session, "end_phase", actor_id=session.state.active_side.value))


def test_initial_aos_state_has_armies_objectives_and_command_points():
    session = _session(seed=3)
    state = session.state

    assert state.system_id == "aos4"
    assert state.active_side is Side.PLAYER
    assert state.phase == "start_of_turn"
    assert state.round == 1
    assert len(state.all_units()) == 11
    assert len(state.objectives) == 4
    assert len(state.terrain) == 5
    assert state.command_points == {"player": 4, "ai": 4}
    assert state.scores == {"player": 0, "ai": 0}
    assert [phase.id for phase in session.system.phases] == [
        "start_of_turn",
        "hero",
        "movement",
        "shooting",
        "charge",
        "combat",
        "end_of_turn",
    ]
    assert [action.action_type for action in session.legal_actions()] == ["end_phase"]


def test_deployment_is_editable_and_ends_into_the_first_battle_round():
    session = GameSession.new(Aos4System(), seed=5, max_rounds=1)
    state = session.state
    assert state.phase == "deployment"
    assert state.command_points == {"player": 0, "ai": 0}

    unit = state.unit_by_id("player-liberators")
    assert unit is not None
    action = _find(session, "deploy", actor_id=unit.id)
    deployment_events = session.apply(action)

    deployed = session.state.unit_by_id(unit.id)
    assert deployed is not None
    assert deployed.position == action.destination
    assert deployed.flags["deployed"]
    assert any(event.kind == "unit_deployed" for event in deployment_events)

    with pytest.raises(IllegalActionError):
        session.apply(
            GameAction(
                action_type="deploy",
                actor_id=unit.id,
                destination=Vec2(20, 15),
            )
        )

    events = session.apply(_find(session, "end_deployment", actor_id=Side.PLAYER.value))
    state = session.state
    assert state.phase == "start_of_turn"
    assert state.active_side is Side.PLAYER
    assert state.round == 1
    assert state.command_points == {"player": 4, "ai": 4}
    assert any(event.kind == "deployment_ended" for event in events)
    assert any(event.kind == "round_started" for event in events)


def test_deployment_rejects_an_out_of_zone_unit():
    session = GameSession.new(Aos4System(), seed=5, max_rounds=1)
    action = GameAction(
        action_type="deploy",
        actor_id="player-liberators",
        destination=Vec2(20, 15),
    )
    validation = session.validate(action)
    assert not validation.ok
    assert any(issue.code == "outside_deployment_zone" for issue in validation.errors)


def test_phase_order_and_transition_events():
    session = _session(seed=5, max_rounds=2)
    events = session.apply(_find(session, "end_phase", actor_id="player"))

    started = next(event for event in events if event.kind == "phase_started")
    assert started.phase == "hero"
    assert started.round == 1

    for expected in ("movement", "shooting", "charge", "combat", "end_of_turn"):
        _end_phase(session)
        assert session.state.phase == expected

    events = session.apply(_find(session, "end_phase", actor_id="player"))
    assert session.state.active_side is Side.AI
    assert session.state.phase == "start_of_turn"
    assert session.state.round == 1
    turn_started = next(event for event in events if event.kind == "turn_started")
    assert turn_started.side == "ai"
    assert turn_started.phase == "start_of_turn"


def test_normal_move_run_and_retreat():
    session = _session(seed=5)
    _set_phase(session, "movement")
    unit = session.state.unit_by_id("player-prosecutors")
    assert unit is not None
    action = _find(session, "move", actor_id=unit.id)
    origin = unit.position
    session.apply(action)
    unit = session.state.unit_by_id(action.actor_id)
    assert unit is not None

    assert unit.flags["moved"]
    assert unit.position.distance_to(origin) <= unit.move + 1e-6

    session = _session(seed=5)
    _set_phase(session, "movement")
    unit = session.state.unit_by_id("player-prosecutors")
    assert unit is not None
    run = _find(session, "run", actor_id=unit.id)
    events = session.apply(run)
    rolled = next(event for event in events if event.kind == "unit_ran").data["roll"]
    unit = session.state.unit_by_id(run.actor_id)
    assert unit is not None

    assert unit.flags["advanced"]
    assert unit.position.distance_to(Vec2(10, 23)) <= unit.move + rolled + 1e-6

    session = _session(seed=5)
    _set_phase(session, "movement")
    liberators = session.state.unit_by_id("player-liberators")
    clanrats = session.state.unit_by_id("ai-clanrats")
    assert liberators is not None and clanrats is not None
    liberators.position = Vec2(20, 15)
    clanrats.position = Vec2(22, 15)
    before_wounds = liberators.wounds
    retreat = _find(session, "retreat", actor_id=liberators.id)
    events = session.apply(retreat)
    liberators = session.state.unit_by_id(retreat.actor_id)
    assert liberators is not None

    assert liberators.flags["advanced"]
    assert liberators.wounds < before_wounds
    assert any(event.kind == "unit_retreated" for event in events)
    assert all(
        liberators.position.distance_to(enemy.position) > 3
        for enemy in session.state.alive_units_for(Side.AI)
    )


def test_shooting_rolls_dice_and_reports_cover():
    session = _session(seed=1)
    _set_phase(session, "shooting")
    prosecutor = session.state.unit_by_id("player-prosecutors")
    clanrats = session.state.unit_by_id("ai-clanrats")
    assert prosecutor is not None and clanrats is not None
    prosecutor.position = Vec2(20, 15)
    clanrats.position = Vec2(25, 15)

    action = _find(session, "shoot", actor_id=prosecutor.id, target_id=clanrats.id)
    cursor = session.state.dice.cursor
    events = session.apply(action)
    attack = next(event for event in events if event.kind == "attack_resolved")

    assert session.state.dice.cursor > cursor
    assert attack.data["attacker"] == action.actor_id
    assert attack.data["ranged"] is True
    assert attack.data["cover"] is False

    session = _session(seed=1)
    _set_phase(session, "shooting")
    prosecutor = session.state.unit_by_id("player-prosecutors")
    clanrats = session.state.unit_by_id("ai-clanrats")
    assert prosecutor is not None and clanrats is not None
    prosecutor.position = Vec2(28, 8.75)
    clanrats.position = Vec2(33.5, 8.75)
    action = _find(session, "shoot", actor_id=prosecutor.id, target_id=clanrats.id)
    events = session.apply(action)
    attack = next(event for event in events if event.kind == "attack_resolved")

    assert attack.data["cover"] is True
    assert attack.data["hit_modifier"] == -1


def test_charge_succeeds_and_fails_with_the_expected_roll():
    session = _session(seed=1)
    _set_phase(session, "charge")
    prosecutor = session.state.unit_by_id("player-prosecutors")
    seer = session.state.unit_by_id("ai-grey-seer")
    assert prosecutor is not None and seer is not None
    prosecutor.position = Vec2(20, 15)
    seer.position = Vec2(25, 15)

    action = _find(session, "charge", actor_id=prosecutor.id, target_id=seer.id)
    events = session.apply(action)
    prosecutor = session.state.unit_by_id(action.actor_id)
    seer = session.state.unit_by_id(action.target_id or "")
    assert prosecutor is not None and seer is not None

    assert prosecutor.flags["charged"]
    assert prosecutor.stats["charge_turn"] == session.state.metadata["turn_number"]
    assert any(event.kind == "charge_succeeded" for event in events)
    edge = max(
        0.0,
        prosecutor.position.distance_to(seer.position) - prosecutor.base_radius - seer.base_radius,
    )
    assert edge <= 0.5 + 1e-9

    session = _session(seed=7)
    _set_phase(session, "charge")
    prosecutor = session.state.unit_by_id("player-prosecutors")
    seer = session.state.unit_by_id("ai-grey-seer")
    assert prosecutor is not None and seer is not None
    prosecutor.position = Vec2(20, 15)
    seer.position = Vec2(27, 15)
    action = _find(session, "charge", actor_id=prosecutor.id, target_id=seer.id)
    origin = prosecutor.position
    events = session.apply(action)
    prosecutor = session.state.unit_by_id(action.actor_id)
    assert prosecutor is not None

    assert prosecutor.position == origin
    assert any(event.kind == "charge_failed" for event in events)


def test_combat_alternates_between_players():
    session = _session(seed=1)
    _set_phase(session, "combat")
    liberators = session.state.unit_by_id("player-liberators")
    clanrats = session.state.unit_by_id("ai-clanrats")
    assert liberators is not None and clanrats is not None
    liberators.position = Vec2(20, 15)
    clanrats.position = Vec2(22, 15)

    player_fights = [action for action in session.legal_actions() if action.action_type == "fight"]
    assert player_fights
    assert all(
        session.state.unit_by_id(action.actor_id).side is Side.PLAYER for action in player_fights
    )

    session.apply(_find(session, "fight", actor_id=liberators.id, target_id=clanrats.id))
    assert session.state.metadata["combat_last_side"] == "player"

    ai_fights = [action for action in session.legal_actions() if action.action_type == "fight"]
    assert ai_fights
    assert all(session.state.unit_by_id(action.actor_id).side is Side.AI for action in ai_fights)

    session.apply(_find(session, "fight", actor_id=clanrats.id, target_id=liberators.id))
    assert _find(session, "end_phase", actor_id="player")


def test_charged_units_strike_first_even_when_the_opponent_is_active():
    session = _session(seed=1)
    _set_phase(session, "combat")
    liberators = session.state.unit_by_id("player-liberators")
    clanrats = session.state.unit_by_id("ai-clanrats")
    assert liberators is not None and clanrats is not None
    liberators.position = Vec2(20, 15)
    clanrats.position = Vec2(22, 15)
    clanrats.stats["charge_turn"] = session.state.metadata["turn_number"]

    fights = [action for action in session.legal_actions() if action.action_type == "fight"]
    assert fights
    assert all(session.state.unit_by_id(action.actor_id).side is Side.AI for action in fights)
    assert all(action.action_type != "end_phase" for action in session.legal_actions())


def test_commands_spend_points_and_are_limited_per_phase():
    session = _session(seed=1)
    _set_phase(session, "hero")
    unit = session.state.unit_by_id("player-liberators")
    assert unit is not None
    unit.take_damage(3)

    rally = _find(
        session,
        "command",
        actor_id=unit.id,
        payload={"command": "rally"},
    )
    events = session.apply(rally)

    assert session.state.command_points["player"] == 3
    assert any(event.kind == "command_used" for event in events)
    assert not [
        action
        for action in session.legal_actions()
        if action.action_type == "command" and action.payload.get("command") == "rally"
    ]


def test_all_out_attack_changes_the_next_attack_roll():
    session = _session(seed=1)
    _set_phase(session, "shooting")
    prosecutor = session.state.unit_by_id("player-prosecutors")
    clanrats = session.state.unit_by_id("ai-clanrats")
    assert prosecutor is not None and clanrats is not None
    prosecutor.position = Vec2(20, 15)
    clanrats.position = Vec2(25, 15)

    command = _find(
        session,
        "command",
        actor_id=prosecutor.id,
        payload={"command": "all_out_attack"},
    )
    session.apply(command)
    prosecutor = session.state.unit_by_id(command.actor_id)
    assert prosecutor is not None
    assert prosecutor.stats["all_out_attack"] == "1:shooting"
    assert session.state.command_points["player"] == 3

    shoot = _find(session, "shoot", actor_id=prosecutor.id, target_id=clanrats.id)
    events = session.apply(shoot)
    attack = next(event for event in events if event.kind == "attack_resolved")
    assert attack.data["hit_modifier"] == 1


def test_objective_control_and_end_of_turn_scoring():
    session = _session(seed=1, max_rounds=2)
    liberators = session.state.unit_by_id("player-liberators")
    clanrats = session.state.unit_by_id("ai-clanrats")
    assert liberators is not None and clanrats is not None
    liberators.position = Vec2(14, 15)
    clanrats.position = Vec2(30, 15)
    _set_phase(session, "end_of_turn")

    events = session.apply(_find(session, "end_phase", actor_id="player"))
    west = next(obj for obj in session.state.objectives if obj.id == "west-crossing")
    east = next(obj for obj in session.state.objectives if obj.id == "east-crossing")

    assert west.controller is Side.PLAYER
    assert east.controller is Side.AI
    assert session.state.scores == {"player": 1, "ai": 0}
    assert any(event.kind == "objective_scored" for event in events)
    assert session.state.active_side is Side.AI

    _set_phase(session, "end_of_turn")
    session.apply(_find(session, "end_phase", actor_id="ai"))
    assert session.state.scores == {"player": 1, "ai": 1}
    assert session.state.round == 2
    assert session.state.active_side is Side.PLAYER


def test_all_enumerated_actions_are_legal_across_a_full_round():
    session = _session(seed=9, max_rounds=2)
    seen_phases = set()
    for _ in range(20):
        if session.is_terminal():
            break
        seen_phases.add(session.state.phase)
        for action in session.legal_actions():
            validation = session.validate(action)
            assert validation.ok, (action, validation.errors)
        _end_phase(session)

    assert {
        "start_of_turn",
        "hero",
        "movement",
        "shooting",
        "charge",
        "combat",
        "end_of_turn",
    }.issubset(seen_phases)


def test_save_and_load_continue_deterministically(tmp_path):
    session = _session(seed=13)
    _set_phase(session, "movement")
    move = _find(session, "move", actor_id="player-liberators")
    session.apply(move)
    path = session.save(tmp_path / "aos4.json")

    loaded = GameSession.from_json(Aos4System(), path.read_text(encoding="utf-8"))
    assert loaded.to_json() == session.to_json()

    for game in (session, loaded):
        _end_phase(game)
    assert session.to_json() == loaded.to_json()


def test_aggression_changes_charge_valuation():
    session = _session(seed=1)
    _set_phase(session, "charge")
    prosecutor = session.state.unit_by_id("player-prosecutors")
    seer = session.state.unit_by_id("ai-grey-seer")
    assert prosecutor is not None and seer is not None
    prosecutor.position = Vec2(20, 15)
    seer.position = Vec2(25, 15)
    charge = _find(session, "charge", actor_id=prosecutor.id, target_id=seer.id)

    aggressive = session.system.evaluate_action(
        session.state, charge, Side.PLAYER, PROFILES["aggressive"].weights()
    )
    cautious = session.system.evaluate_action(
        session.state, charge, Side.PLAYER, PROFILES["cautious"].weights()
    )

    assert aggressive > cautious


def test_decision_is_explainable_and_ai_turn_is_deterministic():
    first = _session(seed=21)
    second = _session(seed=21)
    decision = UtilityAI(first.system, get_profile("balanced")).choose(first.state)
    assert decision is not None
    assert decision.reason

    for game in (first, second):
        run_ai_turn(game, get_profile("balanced"), max_actions=300)
    assert first.to_dict() == second.to_dict()


def test_full_ai_game_completes_and_replays_from_the_action_log():
    initial = _session(seed=31, max_rounds=1)
    initial_json = initial.to_json()
    game = GameSession.from_json(Aos4System(), initial_json)
    turns = 0
    while not game.is_terminal():
        turns += 1
        assert turns < 20
        decisions = run_ai_turn(game, get_profile("balanced"), max_actions=300)
        assert decisions

    assert game.state.status == "complete"
    assert game.state.round == 2
    assert game.state.metadata["winner"] in ("player", "ai", "draw")
    assert any(event.kind == "game_complete" for event in game.state.events)

    replayed = GameSession.from_json(Aos4System(), initial_json)
    for raw_action in game.state.actions:
        replayed.apply(GameAction.from_dict(raw_action))
    assert replayed.to_dict() == game.to_dict()


def test_action_keys_distinguish_commands_and_phase_payloads():
    session = _session(seed=1)
    _set_phase(session, "shooting")

    command_actions = [
        action for action in session.legal_actions() if action.action_type == "command"
    ]
    keys = [action.key() for action in command_actions]
    assert len(keys) == len(set(keys))

    end_phase = _find(session, "end_phase", actor_id="player")
    assert end_phase.payload["phase"] == "shooting"
