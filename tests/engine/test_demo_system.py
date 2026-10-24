from typing import Optional

import pytest

from backend.engine.ai.policy import PROFILES, UtilityAI, get_profile, run_ai_turn
from backend.engine.core.geometry import Vec2
from backend.engine.core.models import Side
from backend.engine.core.session import GameSession
from backend.engine.core.validation import validate_state
from backend.engine.systems.base import GameAction, IllegalActionError
from backend.engine.systems.demo import DemoSystem


@pytest.fixture
def session() -> GameSession:
    return GameSession.new(DemoSystem(), seed=17, max_rounds=1)


def _action(session: GameSession, action_type: str, actor_id: Optional[str] = None):
    for action in session.legal_actions():
        if action.action_type != action_type:
            continue
        if actor_id is None or action.actor_id == actor_id:
            return action
    raise AssertionError(f"no {action_type} action for {actor_id!r}")


def test_initial_game_is_valid_and_has_expected_phases(session):
    state = session.state
    assert validate_state(state).ok
    assert [phase.id for phase in session.system.phases] == ["movement", "shooting"]
    assert state.active_side is Side.PLAYER
    assert state.phase == "movement"
    assert session.legal_actions()
    assert any(action.action_type == "move" for action in session.legal_actions())
    assert all(action.action_type != "shoot" for action in session.legal_actions())


def test_move_updates_position_and_records_event(session):
    action = _action(session, "move", "player-vanguard")
    before = session.state.unit_by_id("player-vanguard")
    assert before is not None
    original = before.position

    events = session.apply(action)
    after = session.state.unit_by_id("player-vanguard")

    assert after is not None
    assert after.position == action.destination
    assert after.position.distance_to(original) <= after.move + 1e-6
    assert after.flags["moved"]
    assert any(event.kind == "unit_moved" for event in events)
    assert events[0].seq == 1
    assert events[0].phase == "movement"


def test_illegal_move_is_rejected_without_mutating_state(session):
    before = session.to_dict()
    action = GameAction(
        action_type="move",
        actor_id="player-vanguard",
        destination=session.state.unit_by_id("player-vanguard").position + Vec2(100, 0),
    )

    with pytest.raises(IllegalActionError):
        session.apply(action)
    assert session.to_dict() == before


def test_shoot_action_resolves_attack_and_advances_cursor(session):
    movement = _action(session, "move", "player-vanguard")
    session.apply(movement)
    session.apply(_action(session, "end_phase"))

    shoot_actions = [action for action in session.legal_actions() if action.action_type == "shoot"]
    # The vanguard starts within 24" of the raider mob.
    assert shoot_actions
    cursor_before = session.state.dice.cursor
    events = session.apply(shoot_actions[0])

    assert session.state.dice.cursor > cursor_before
    attack = next(event for event in events if event.kind == "attack_resolved")
    assert attack.data["attacker"] == shoot_actions[0].actor_id
    assert attack.data["hits"] + attack.data["wounds"] >= 0


def test_phase_and_turn_transitions(session):
    session.apply(_action(session, "end_phase"))
    assert session.state.phase == "shooting"

    session.apply(_action(session, "end_phase"))
    assert session.state.active_side is Side.AI
    assert session.state.phase == "movement"
    assert session.state.round == 1


def test_invalid_phase_and_target_are_rejected(session):
    with pytest.raises(IllegalActionError):
        session.apply(
            GameAction(action_type="shoot", actor_id="player-vanguard", target_id="ai-raiders")
        )

    session.apply(_action(session, "end_phase"))
    with pytest.raises(IllegalActionError):
        session.apply(
            GameAction(
                action_type="shoot",
                actor_id="player-vanguard",
                target_id="player-captain",
            )
        )


def test_ai_always_chooses_legal_actions_and_can_finish_a_game():
    session = GameSession.new(DemoSystem(), seed=5, max_rounds=2)
    decisions = []

    total = 0
    while not session.is_terminal():
        decisions.extend(run_ai_turn(session, get_profile("balanced"), max_actions=100))
        total += 1
        assert total < 40, "AI loop did not terminate"

    assert decisions
    assert session.state.status == "complete"
    assert session.state.round == 3
    assert any(event.kind == "turn_ended" for event in session.state.events)


def test_same_seed_and_profiles_replay_identically():
    def play() -> dict:
        game = GameSession.new(DemoSystem(), seed=101, max_rounds=1)
        while not game.is_terminal():
            run_ai_turn(game, PROFILES["aggressive"])
        return game.to_dict()

    assert play() == play()


def test_aggression_changes_how_actions_are_valued():
    session = GameSession.new(DemoSystem(), seed=3, max_rounds=1)
    system = session.system
    state = session.state
    approach = next(
        action
        for action in session.legal_actions()
        if action.action_type == "move" and "approach" in action.tags
    )

    aggressive_score = system.evaluate_action(
        state, approach, Side.PLAYER, PROFILES["aggressive"].weights()
    )
    cautious_score = system.evaluate_action(
        state, approach, Side.PLAYER, PROFILES["cautious"].weights()
    )

    assert aggressive_score > cautious_score


def test_decision_is_explainable_and_has_alternatives(session):
    policy = UtilityAI(session.system, PROFILES["balanced"])
    decision = policy.choose(session.state)

    assert decision is not None
    assert decision.action.action_type == "move"
    assert decision.reason
    assert decision.alternatives
    assert decision.score >= decision.alternatives[0].score


def test_save_and_load_continue_deterministically(session, tmp_path):
    session.apply(_action(session, "move", "player-vanguard"))
    path = session.save(tmp_path / "game.json")

    loaded = GameSession.from_json(DemoSystem(), path.read_text())
    assert loaded.to_json() == session.to_json()

    # Applying the same next action to both copies produces the same result.
    for game in (session, loaded):
        game.apply(_action(game, "end_phase"))
    assert session.to_json() == loaded.to_json()


def test_every_enumerated_action_is_legal(session):
    for action in session.legal_actions():
        assert session.validate(action).ok, action

    session.apply(_action(session, "end_phase"))
    for action in session.legal_actions():
        assert session.validate(action).ok, action


def test_objective_scores_at_the_end_of_the_battle_round():
    game = GameSession.new(DemoSystem(), seed=29, max_rounds=1)
    vanguard = game.state.unit_by_id("player-vanguard")
    assert vanguard is not None
    vanguard.position = Vec2(22, 15)

    for _ in range(4):
        game.apply(_action(game, "end_phase"))

    assert game.is_terminal()
    assert game.state.objectives[0].controller is Side.PLAYER
    assert game.state.score_for(Side.PLAYER) == 2
    assert any(event.kind == "objective_scored" for event in game.state.events)


def test_action_log_replays_a_saved_game_exactly():
    initial = GameSession.new(DemoSystem(), seed=71, max_rounds=1)
    state_text = initial.to_json()

    game = GameSession.from_json(DemoSystem(), state_text)
    for _ in range(4):
        game.apply(_action(game, "end_phase"))

    replayed = GameSession.from_json(DemoSystem(), state_text)
    for raw_action in game.state.actions:
        replayed.apply(GameAction.from_dict(raw_action))

    assert replayed.to_dict() == game.to_dict()
