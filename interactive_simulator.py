"""Interactive (or automatic) simulator front-end.

This provides a lightweight CLI to create a player army (or use a sample),
runs the AI SoloSimulator from `full_simulator.py`, and resolves simple
combat when AI actions instruct attacks. Combat resolution is intentionally
simplified: each model makes `attacks` attacks; to-hit/to-wound/save are
resolved with d6 comparisons; wounds are subtracted from units and models
are removed when their wounds run out.

This is not a full AoS rules engine—it's a decision/combat harness that
lets you interactively test card-driven AI behavior and see concrete
outcomes.
"""

import argparse
import math
import random
from copy import deepcopy
from typing import List, Optional, Callable

from full_simulator import SoloSimulator, Unit as AIUnit
from battlescribe_parser import parse_battlescribe_html


class Unit:
    def __init__(self, name: str, models: int, wounds_per_model: int, attacks: int, to_hit: int, to_wound: int, save: int, aggression: str = 'Neutral'):
        self.name = name
        self.models = models
        self.wounds_per_model = wounds_per_model
        self.attacks = attacks
        self.to_hit = to_hit  # e.g., 4 means 4+
        self.to_wound = to_wound
        self.save = save
        self.current_wounds = models * wounds_per_model
        self.aggression = aggression

    @property
    def models_remaining(self):
        return math.ceil(self.current_wounds / self.wounds_per_model)

    def is_alive(self):
        return self.models_remaining > 0

    def take_wounds(self, wounds: int):
        self.current_wounds = max(0, self.current_wounds - wounds)

    def __repr__(self):
        return f"Unit(name={self.name!r}, models={self.models_remaining}/{self.models}, wounds={self.current_wounds})"


def roll_d6():
    return random.randint(1, 6)


def _roll_damage(dmg):
    """Roll damage which can be an int or a dict {'type':'D','sides':n}."""
    if isinstance(dmg, dict) and dmg.get('type') == 'D':
        sides = dmg.get('sides', 3)
        return random.randint(1, sides)
    return int(dmg)


def resolve_attack(attacker: Unit, defender: Unit, weapon: dict = None):
    """Resolve an attack using weapon profile when provided.

    weapon: {'attacks', 'to_hit', 'to_wound', 'rend', 'damage'} or None
    If weapon is None, use attacker's base stats.
    """
    atk_attacks = attacker.models_remaining * (weapon.get('attacks') if weapon else attacker.attacks)
    hits = 0
    wounds = 0
    unsaved = 0

    to_hit = (weapon.get('to_hit') if weapon else attacker.to_hit)
    to_wound = (weapon.get('to_wound') if weapon else attacker.to_wound)
    rend = (weapon.get('rend') if weapon else 0)
    damage_profile = (weapon.get('damage') if weapon else 1)

    for _ in range(atk_attacks):
        if roll_d6() >= to_hit:
            hits += 1
            if roll_d6() >= to_wound:
                wounds += 1
                # defender saves
                save_needed = max(2, defender.save - rend)
                if roll_d6() < save_needed:
                    # unsaved wound: roll damage for this unsaved wound
                    dmg = _roll_damage(damage_profile)
                    unsaved += 1
                    defender.take_wounds(dmg)

    return {
        'attacks': atk_attacks,
        'hits': hits,
        'wounds': wounds,
        'unsaved_instances': unsaved,
        'defender_remaining_wounds': defender.current_wounds,
        'defender_models_remaining': defender.models_remaining,
    }


def sample_armies():
    player_units = [
        Unit('Player Guard A', models=10, wounds_per_model=1, attacks=1, to_hit=4, to_wound=4, save=6, aggression='Neutral'),
        Unit('Player Hero', models=1, wounds_per_model=3, attacks=2, to_hit=4, to_wound=4, save=5, aggression='Neutral'),
    ]

    ai_units = [
        AIUnit('Mournfang Pack A', aggression='Aggressive', keywords=['Battleline','Cavalry']),
        AIUnit('Huskard on Stonehorn', aggression='Aggressive', keywords=['Hero','Monster']),
        AIUnit('Icebrow Hunter', aggression='Neutral', keywords=['Hero']),
    ]

    return player_units, ai_units


def run_simulation(player_units: List[Unit], ai_units: List[AIUnit], turns: int = 5, seed: int = 1, auto: bool = False,
                   event_callback: Optional[Callable[[dict], None]] = None):
    random.seed(seed)
    sim = SoloSimulator(ai_units, seed=seed)

    for t in range(turns):
        print(f"\n=== TURN {t+1} ===")
        inp = None
        if not auto:
            inp = input("Press Enter to run AI turn, or type 'quit' to exit: ")
            if inp.strip().lower() == 'quit':
                break

        log = sim.simulate_turn()
        # Print compact log and emit structured events via event_callback when provided
        for entry in log:
            if 'unit' in entry and 'aggression_check' in entry:
                msg = f"AI check: {entry['unit']} -> {'ACT' if entry['aggression_check'] else 'HOLD'}"
                if event_callback:
                    event_callback({'type': 'aggression_check', 'unit': entry['unit'], 'act': bool(entry['aggression_check']), 'text': msg})
                else:
                    print(msg)
            elif 'action_resolved' in entry:
                ar = entry['action_resolved']
                msg = f"AI action: {ar['unit']} -> {ar['card_title']} ({ar['initiative']})"
                if event_callback:
                    event_callback({'type': 'ai_action', 'unit': ar['unit'], 'card_title': ar['card_title'], 'initiative': ar['initiative'], 'behavior': ar.get('behavior', ''), 'text': msg})
                else:
                    print(msg)

                behavior = (ar.get('behavior') or '').lower()
                # Simple mapping: if behavior contains 'attack', 'charge', 'smash', resolve attack vs first alive player unit
                if any(k in behavior for k in ['attack', 'charge', 'smash', 'kill', 'trample', 'krump', 'slay']):
                    # pick first alive player unit
                    target = next((u for u in player_units if u.is_alive()), None)
                    if target:
                        # Use simplified attacker stats: map AIUnit keywords to basic stats
                        # For monsters/heroes, use stronger template
                        if 'Monster' in ar.get('behavior','') or 'monster' in ar.get('behavior','') or 'Monster' in ar.get('card_title',''):
                            atk = Unit(ar['unit'], models=1, wounds_per_model=3, attacks=3, to_hit=3, to_wound=3, save=6)
                        elif 'hero' in (ar.get('behavior','').lower() + ar.get('card_title','').lower()):
                            atk = Unit(ar['unit'], models=1, wounds_per_model=2, attacks=2, to_hit=4, to_wound=4, save=5)
                        else:
                            # generic AI battleline
                            atk = Unit(ar['unit'], models=3, wounds_per_model=1, attacks=1, to_hit=4, to_wound=4, save=6)

                        res = resolve_attack(atk, target)
                        detail = f"Resolved attack vs {target.name}: {res['unsaved_instances']} unsaved wound instances, target now {res['defender_models_remaining']} models ({res['defender_remaining_wounds']} wounds)"
                        if event_callback:
                            event_callback({'type': 'combat', 'attacker': ar['unit'], 'defender': target.name, 'result': res, 'text': detail})
                        else:
                            print(f"  -> {detail}")
                    else:
                        if event_callback:
                            event_callback({'type': 'combat', 'text': 'No player units remain to attack'})
                        else:
                            print("  -> No player units remain to attack")

        # After AI turn, optionally allow player to auto-attack
        if any(u.is_alive() for u in player_units):
            if not auto:
                cmd = input("Type 'auto' for auto-player attack on nearest AI, Enter to skip: ")
                if cmd.strip().lower() == 'auto':
                    # player attacks first alive AI unit
                    target_ai = next((u for u in ai_units if True), None)
                    # We don't have detailed AI unit stats; use a generic template
                    ai_target_name = target_ai.name if target_ai else 'AI'
                    # find player unit to attack
                    attacker = next((p for p in player_units if p.is_alive()), None)
                    if attacker and target_ai:
                        # convert AIUnit to Unit template for defense
                        def_unit = Unit(ai_target_name, models=3, wounds_per_model=1, attacks=1, to_hit=4, to_wound=4, save=6)
                        # If the player unit has weapons parsed from a roster, prefer its first weapon
                        weapon = getattr(attacker, 'weapons', None)
                        if weapon and len(weapon) > 0:
                            w = weapon[0]
                            rr = resolve_attack(attacker, def_unit, weapon=w)
                            title = w.get('title') or w.get('name') or 'weapon'
                            text = f"Player {attacker.name} attacked {ai_target_name} with {title}: {rr['unsaved_instances']} unsaved wound instances (ai sim results abstract)."
                            if event_callback:
                                event_callback({'type': 'player_attack', 'attacker': attacker.name, 'defender': ai_target_name, 'weapon': title, 'result': rr, 'text': text})
                            else:
                                print(text)
                        else:
                            rr = resolve_attack(attacker, def_unit)
                            text = f"Player {attacker.name} attacked {ai_target_name}: {rr['unsaved_instances']} unsaved wound instances (ai sim results abstract)."
                            if event_callback:
                                event_callback({'type': 'player_attack', 'attacker': attacker.name, 'defender': ai_target_name, 'result': rr, 'text': text})
                            else:
                                print(text)
            else:
                # in auto mode, let the first alive player unit auto-attack the first AI target
                target_ai = next((u for u in ai_units if True), None)
                attacker = next((p for p in player_units if p.is_alive()), None)
                if attacker and target_ai:
                    ai_target_name = target_ai.name
                    def_unit = Unit(ai_target_name, models=3, wounds_per_model=1, attacks=1, to_hit=4, to_wound=4, save=6)
                    weapon = getattr(attacker, 'weapons', None)
                    if weapon and len(weapon) > 0:
                        w = weapon[0]
                        rr = resolve_attack(attacker, def_unit, weapon=w)
                        title = w.get('title') or w.get('name') or 'weapon'
                        text = f"Player {attacker.name} (auto) attacked {ai_target_name} with {title}: {rr['unsaved_instances']} unsaved wound instances (ai sim results abstract)."
                        if event_callback:
                            event_callback({'type': 'player_attack', 'attacker': attacker.name, 'defender': ai_target_name, 'weapon': title, 'result': rr, 'text': text})
                        else:
                            print(text)
                    else:
                        rr = resolve_attack(attacker, def_unit)
                        text = f"Player {attacker.name} (auto) attacked {ai_target_name}: {rr['unsaved_instances']} unsaved wound instances (ai sim results abstract)."
                        if event_callback:
                            event_callback({'type': 'player_attack', 'attacker': attacker.name, 'defender': ai_target_name, 'result': rr, 'text': text})
                        else:
                            print(text)

        # Show summary
        summary_texts = []
        summary_texts.append("\n-- Army Status --")
        for p in player_units:
            summary_texts.append(f"{p.name}: {p.models_remaining} models, {p.current_wounds} wounds total")

        if event_callback:
            event_callback({'type': 'summary', 'lines': summary_texts, 'text': '\n'.join(summary_texts)})
        else:
            print("\n-- Army Status --")
            for p in player_units:
                print(f"{p.name}: {p.models_remaining} models, {p.current_wounds} wounds total")

    if event_callback:
        event_callback({'type': 'finished', 'text': 'Simulation finished.'})
    else:
        print("\nSimulation finished.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true', help='Run in non-interactive auto mode')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--roster', type=str, default=None, help='Path to a BattleScribe HTML roster to import as player army')
    args = parser.parse_args()

    print("Interactive Solo Simulator")
    player_units = None
    ai_units = None

    if args.roster:
        try:
            parsed = parse_battlescribe_html(args.roster)
            # Create Unit instances in the same order as parsed. Do not aggregate duplicates.
            player_units = []
            for u in parsed:
                unit = Unit(u['name'], models=u.get('models', 1), wounds_per_model=u.get('wounds_per_model', 1),
                            attacks=u.get('attacks', 1), to_hit=u.get('to_hit', 4), to_wound=u.get('to_wound', 4),
                            save=u.get('save', 6))
                # attach weapons list for later use
                setattr(unit, 'weapons', u.get('weapons', []))
                player_units.append(unit)
            print(f"Imported {len(player_units)} player units from {args.roster}")
        except Exception as e:
            print(f"Failed to parse roster {args.roster}: {e}")
            print("Falling back to sample armies.")
            player_units, ai_units = sample_armies()
    else:
        choice = input("Type 'sample' to use sample armies or Enter to use sample: ")
        player_units, ai_units = sample_armies()

    # If ai_units wasn't set by sample_armies fallback above, set it now
    if ai_units is None:
        _, ai_units = sample_armies()

    run_simulation(player_units, ai_units, turns=5, seed=args.seed, auto=args.auto)


if __name__ == '__main__':
    main()
