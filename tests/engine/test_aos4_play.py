import pytest

from backend.engine.core.models import Side
from backend.engine.systems.aos4.play import Aos4Match


@pytest.mark.parametrize("entry_point", ["resume", "apply_player_action"])
def test_ai_movement_labels_use_the_pre_action_position(entry_point):
    match = Aos4Match.create(seed=7, ai_profile="balanced", max_rounds=2)
    state = match.session.state
    origins = {unit.id: unit.position for unit in state.units_for(Side.AI)}
    if entry_point == "resume":
        state.active_side = Side.AI
        state.phase = "movement"
        events, decisions = match.resume()
    else:
        state.phase = "end_of_turn"
        action = next(
            entry["action"]
            for entry in match.player_actions()
            if entry["action_type"] == "end_phase"
        )
        events, decisions = match.apply_player_action(action)

    snapshot = match.snapshot(events=events, decisions=decisions)
    movements = [
        decision
        for decision in snapshot["ai_decisions"]
        if decision["action"]["action_type"] in ("move", "run", "retreat")
    ]
    assert movements, "the AI must move to exercise the label regression"
    for decision in movements:
        action = next(
            item.action for item in decisions if item.action.to_dict() == decision["action"]
        )
        distance = origins[action.actor_id].distance_to(action.destination)
        assert distance > 0
        assert decision["label"] == f'{action.action_type.title()} {distance:.1f}"'
