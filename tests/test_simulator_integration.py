import os
import sys

from backend.battlescribe_parser import parse_battlescribe_html
from backend.full_simulator import SoloSimulator
from backend.full_simulator import Unit as AIUnit

# Ensure repo root is importable so tests can import the project's modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_ai_simulator_runs_with_roster():
    # Use Current Stormcasts.html if present, else skip
    repo_root = os.path.dirname(os.path.dirname(__file__))
    roster_path = os.path.join(repo_root, "Current Stormcasts.html")
    if not os.path.exists(roster_path):
        import pytest

        pytest.skip("BattleScribe fixture not present")

    units = parse_battlescribe_html(roster_path)
    # Build AIUnit list for SoloSimulator from parsed roster
    ai_units = []
    for u in units:
        ai_units.append(AIUnit(u.get("name", "Unit"), aggression=u.get("aggression", "Neutral")))

    sim = SoloSimulator(ai_units, seed=42)
    events = sim.simulate_turn()
    # Expect a list of events; at minimum aggression levels should be present
    assert isinstance(events, list)
    assert any(
        ("event" in e and e["event"] == "aggression_level") or ("action_resolved" in e)
        for e in events
    )


def test_all_units_always_act():
    """All units should receive action cards regardless of aggression level."""
    from backend.full_simulator import SoloSimulator, Unit

    units = [
        Unit("Aggressive Unit", aggression="Aggressive"),
        Unit("Neutral Unit", aggression="Neutral"),
        Unit("Cautious Unit", aggression="Cautious"),
    ]

    sim = SoloSimulator(units, seed=42)
    events = sim.simulate_turn()

    # Extract action assignments
    actions = [e for e in events if "action_resolved" in e]

    # All 3 units should have actions
    assert len(actions) == 3
    unit_names = {a["action_resolved"]["unit"] for a in actions}
    assert unit_names == {"Aggressive Unit", "Neutral Unit", "Cautious Unit"}


def test_aggression_modifiers_included():
    """Verify aggression modifiers are included in action assignments."""
    from backend.full_simulator import AGGRESSION_EXECUTION_MODIFIERS, SoloSimulator, Unit

    units = [
        Unit("Test Aggressive", aggression="Aggressive"),
        Unit("Test Neutral", aggression="Neutral"),
    ]

    sim = SoloSimulator(units, seed=42)
    events = sim.simulate_turn()

    # Check aggression level events
    aggression_events = [e for e in events if e.get("event") == "aggression_level"]
    assert len(aggression_events) == 2

    # Verify modifiers are correct
    aggressive_event = next(e for e in aggression_events if e["unit"] == "Test Aggressive")
    assert aggressive_event["aggression"] == "Aggressive"
    assert aggressive_event["modifiers"] == AGGRESSION_EXECUTION_MODIFIERS["Aggressive"]

    neutral_event = next(e for e in aggression_events if e["unit"] == "Test Neutral")
    assert neutral_event["aggression"] == "Neutral"
    assert neutral_event["modifiers"] == AGGRESSION_EXECUTION_MODIFIERS["Neutral"]


def test_battle_tactic_displayed():
    """Verify battle tactic is logged so players can see the AI's goal."""
    from backend.full_simulator import SoloSimulator, Unit

    units = [
        Unit("Test Unit 1", aggression="Neutral"),
        Unit("Test Unit 2", aggression="Neutral"),
    ]

    sim = SoloSimulator(units, seed=42)
    events = sim.simulate_turn()

    # Check that battle_tactic_drawn event exists
    tactic_events = [e for e in events if e.get("event") == "battle_tactic_drawn"]
    assert len(tactic_events) == 1

    tactic_event = tactic_events[0]
    assert "tactic" in tactic_event
    assert "description" in tactic_event
    assert isinstance(tactic_event["tactic"], str)
    assert len(tactic_event["tactic"]) > 0
