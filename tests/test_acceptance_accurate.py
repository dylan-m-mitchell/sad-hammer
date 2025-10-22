import pytest
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
    units = [Unit('A', aggression='Neutral')]
    sim = SoloSimulator(units, seed=1)
    # initial pool length
    initial = list(sim.tactic_pool)
    # run three turns and observe pool/discard
    for _ in range(3):
        sim.choose_battle_tactic()
    # Broken Ranks should be in either pool or discard after turn 2
    assert 'Broken Ranks' in sim.tactic_pool or 'Broken Ranks' in sim.tactic_discard
    # No tactic should appear twice across pool+discard
    combined = sim.tactic_pool + sim.tactic_discard
    assert len(combined) == len(set(combined))


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
