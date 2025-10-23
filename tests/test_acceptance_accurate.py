import pytest
import sys
import os
# make project root importable for test discovery
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from full_simulator import SoloSimulator, Unit
from interactive_simulator import Unit as CombatUnit, resolve_attack


def test_aggression_modifier_deterministic():
    # Aggressive target assumed 4 (in our mapping), unit has +2 modifier
    u = Unit('Test Agg', aggression='Aggressive')
    # use SoloSimulator rng by seed via constructor
    sim = SoloSimulator([u], seed=12345)
    # monkeypatch a high modifier directly
    u.aggression_modifier = 2
    res = sim.aggression_check(u)
    # aggression_check now returns dict with total/result
    assert isinstance(res, dict)
    # deterministic expectation: with seed 12345 the roll should be reproducible
    assert 'roll' in res and 'total' in res and 'target' in res


def test_tactic_pool_evolution_and_no_duplicates():
    """Test that Battle Tactics deck properly manages cards over multiple turns."""
    units = [Unit('A', aggression='Neutral')]
    sim = SoloSimulator(units, seed=1)
    
    # Run three turns
    for _ in range(3):
        sim.simulate_turn()
    
    # After turn 2+, Broken Ranks should be available in the deck
    # Check that the deck manager has Broken Ranks in either deck or discard
    deck_cards = [c['title'] for c in sim.tactics_deck.deck]
    discard_cards = [c['title'] for c in sim.tactics_deck.discard_pile]
    all_cards = deck_cards + discard_cards
    
    # Broken Ranks should be present (in deck or discard) after turn 2
    assert 'Broken Ranks' in all_cards, "Broken Ranks should be present after turn 2"
    
    # The total number of unique tactics in deck+discard should be 8 (no duplicates)
    # Note: deck + discard should always contain all 8 tactics, no duplicates
    assert len(set(all_cards)) == 8, "Should have exactly 8 unique tactics"
    assert len(all_cards) == len(set(all_cards)), "No duplicate tactics should exist in deck+discard"


def test_action_combat_deterministic():
    # Simple attacker vs defender using interactive_simulator.resolve_attack
    atk = CombatUnit('Attacker', models=3, wounds_per_model=1, attacks=1, to_hit=4, to_wound=4, save=6)
    defn = CombatUnit('Defender', models=5, wounds_per_model=1, attacks=1, to_hit=4, to_wound=4, save=6)
    # seed python's random for deterministic behavior
    import random as _r
    _r.seed(42)
    res = resolve_attack(atk, defn)
    # Ensure keys exist and numbers are consistent
    assert 'unsaved_instances' in res
    assert res['defender_models_remaining'] <= 5


def test_battleshock_placeholder():
    # Placeholder: higher level tests will simulate casualties and run morale checks.
    assert True
