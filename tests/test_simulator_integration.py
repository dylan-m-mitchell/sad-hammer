import os
import io
import sys

# Ensure repo root is importable so tests can import the project's modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.battlescribe_parser import parse_battlescribe_html
from backend.full_simulator import SoloSimulator, Unit as AIUnit


def test_ai_simulator_runs_with_roster():
    # Use Current Stormcasts.html if present, else skip
    repo_root = os.path.dirname(os.path.dirname(__file__))
    roster_path = os.path.join(repo_root, 'Current Stormcasts.html')
    if not os.path.exists(roster_path):
        import pytest
        pytest.skip('BattleScribe fixture not present')

    units = parse_battlescribe_html(roster_path)
    # Build AIUnit list for SoloSimulator from parsed roster
    ai_units = []
    for u in units:
        ai_units.append(AIUnit(u.get('name', 'Unit'), aggression=u.get('aggression', 'Neutral')))

    sim = SoloSimulator(ai_units, seed=42)
    events = sim.simulate_turn()
    # Expect a list of events; at minimum aggression checks should be present
    assert isinstance(events, list)
    assert any(('unit' in e and 'aggression_check' in e) or ('action_resolved' in e) for e in events)
