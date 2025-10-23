"""Full solo AI simulator for Age of Sigmar (card-driven)

This module implements the simulator behavior using the data in
`reference_card_decks.py`. It is standalone and does not modify other
project files. The simulator follows the rules described on the Woehammer
blog and the General's Handbook 2021 conventions where applicable:

- Tactic pool handling: start with 4 tactics (Monstrous Takeover,
  Ferocious Advance, Aggressive Expansion, Conquer). On turn 2 add
  Broken Ranks. On turn 3 add the remaining tactics. Used tactics are
  discarded. One tactic is drawn each turn.
- Action deck: for the chosen tactic, use its action cards and mix in
  ~1/5 of the objective action cards (at least 1) then shuffle.
- Aggression checks: Aggressive=4+, Neutral=5+, Cautious=6+ (d6 roll).
- Per-unit resolution: draw one action per unit that passes the
  aggression check; actions carry initiative values; resolve actions in
  descending initiative order.

This is a behavioural simulator and intentionally does not implement
full AoS rules (movement, combat resolution, dice rolls for attacks,
damage). It executes the card-driven decision process and prints
structured logs that a game-engine or human can use to enact actions.
"""

from copy import deepcopy
import random
from typing import List, Dict, Optional

from reference_card_decks import (
    battle_tactic_deck,
    tactic_to_actions,
    objective_action_deck,
)


# Aggression thresholds (default more likely to ACT than prior mapping)
# These are the d6 target numbers a unit must roll >= to ACT.
# Default: Aggressive 3+ (66%), Neutral 4+ (50%), Cautious 5+ (33%)
AGGRESSION_CHECK_TARGET = {
    "Aggressive": 3,
    "Neutral": 4,
    "Cautious": 5,
}


class Unit:
    def __init__(self, name: str, aggression: str = "Neutral", keywords: Optional[List[str]] = None, aggression_modifier: int = 0):
        self.name = name
        self.aggression = aggression
        self.keywords = keywords or []
        # numeric modifier added to the d6 roll for aggression checks (can be negative)
        self.aggression_modifier = int(aggression_modifier or 0)

    def __repr__(self):
        return f"Unit(name={self.name!r}, aggression={self.aggression!r}, keywords={self.keywords!r})"


class SoloSimulator:
    def __init__(self, units: List[Unit], seed: Optional[int] = None, aggression_thresholds: Optional[Dict[str, int]] = None):
        self.units = units
        self.turn = 1
        self.seed = seed
        # use an instance RNG so we don't alter global random state
        self.rng = random.Random(seed)

        # allow callers to override aggression thresholds for experimentation or tests
        self.aggression_targets = aggression_thresholds or AGGRESSION_CHECK_TARGET

        # Build tactic pool per blog: initial 4 tactics
        self.initial_tactics = [
            'Monstrous Takeover',
            'Ferocious Advance',
            'Aggressive Expansion',
            'Conquer',
        ]
        # remaining tactics that get added later
        self.remaining_tactics = [t['title'] for t in battle_tactic_deck if t['title'] not in self.initial_tactics]

        self.tactic_pool = list(self.initial_tactics)
        self.tactic_discard: List[str] = []

    def aggression_check(self, unit: Unit) -> Dict:
        """Perform an aggression check and return a dict with details.

        Returns a dict: {
            'result': bool,
            'roll': int,
            'modifier': int,
            'total': int,
            'target': int
        }
        """
        target = self.aggression_targets.get(unit.aggression, 5)
        roll = self.rng.randint(1, 6)
        modifier = int(getattr(unit, 'aggression_modifier', 0) or 0)
        total = roll + modifier
        result = total >= target
        return {'result': result, 'roll': roll, 'modifier': modifier, 'total': total, 'target': target}

    def choose_battle_tactic(self) -> Optional[str]:
        # add Broken Ranks on turn 2
        if self.turn >= 2 and 'Broken Ranks' not in self.tactic_pool and 'Broken Ranks' not in self.tactic_discard:
            self.tactic_pool.append('Broken Ranks')

        # add remaining tactics on turn 3
        if self.turn >= 3:
            for t in list(self.remaining_tactics):
                if t not in self.tactic_pool and t not in self.tactic_discard:
                    self.tactic_pool.append(t)

        if not self.tactic_pool:
            return None

        choice = self.rng.choice(self.tactic_pool)
        # move to discard
        self.tactic_pool.remove(choice)
        self.tactic_discard.append(choice)
        return choice

    def build_action_deck(self, tactic_title: str) -> List[Dict]:
        # Copy tactic actions
        tactic_actions = deepcopy(tactic_to_actions.get(tactic_title, []))
        # Determine how many objective cards to mix in (roughly 1/5 of objective deck)
        num_obj = max(1, len(objective_action_deck) // 5) if objective_action_deck else 0
        mixed = list(tactic_actions)
        if num_obj > 0:
            mixed.extend(deepcopy(self.rng.sample(objective_action_deck, min(num_obj, len(objective_action_deck)))))
        self.rng.shuffle(mixed)
        return mixed

    def remove_unit(self, unit_name: str) -> bool:
        """Remove a unit from the simulation (e.g., when killed by the player).
        
        Args:
            unit_name: The name of the unit to remove
            
        Returns:
            True if unit was found and removed, False otherwise
        """
        for i, unit in enumerate(self.units):
            if unit.name == unit_name:
                self.units.pop(i)
                return True
        return False

    def simulate_turn(self) -> List[Dict]:
        """Simulate a single AI turn; returns a list of resolved action records."""
        log = []
        tactic = self.choose_battle_tactic()
        if tactic is None:
            log.append({"event": "no_tactic_available"})
            return log

        action_deck = self.build_action_deck(tactic)

        # For each unit, perform aggression check and draw an action if it passes
        drawn_actions = []  # tuples of (unit, card)
        discard_pile = []

        for u in self.units:
            check = self.aggression_check(u)
            will_act = check['result']
            # include debug fields so a client can see the roll and modifier
            log.append({
                "unit": u.name,
                "aggression_check": will_act,
                "roll": check['roll'],
                "modifier": check['modifier'],
                "total": check['total'],
                "target": check['target'],
            })
            if will_act:
                # draw a card non-destructively: pop from front
                if not action_deck:
                    # if empty, rebuild (rare) -- rebuild without objective mix to avoid infinite loop
                    action_deck = deepcopy(tactic_to_actions.get(tactic, []))
                    self.rng.shuffle(action_deck)
                card = action_deck.pop(0)
                discard_pile.append(card)
                # ensure initiative exists
                initiative = card.get('initiative', 0)
                drawn_actions.append({"unit": u, "card": card, "initiative": initiative})

        # Resolve actions in descending initiative order
        drawn_actions.sort(key=lambda x: x['initiative'], reverse=True)
        for item in drawn_actions:
            u = item['unit']
            card = item['card']
            rec = {
                "turn": self.turn,
                "tactic": tactic,
                "unit": u.name,
                "card_title": card.get('title'),
                "initiative": item['initiative'],
                "behavior": card.get('behavior'),
            }
            # simple textual resolution: append to log
            log.append({"action_resolved": rec})

        self.turn += 1
        return log


def demo_run(turns: int = 3, seed: Optional[int] = 1):
    # Example units (these would come from your army lists in a real sim)
    units = [
        Unit("Mournfang Pack A", aggression="Aggressive", keywords=["Battleline", "Cavalry"]),
        Unit("Huskard on Stonehorn", aggression="Aggressive", keywords=["Hero", "Monster"]),
        Unit("Icebrow Hunter", aggression="Neutral", keywords=["Hero"]),
    ]

    sim = SoloSimulator(units, seed=seed)
    for t in range(turns):
        print(f"=== Turn {sim.turn} ===")
        out = sim.simulate_turn()
        for o in out:
            print(o)
        print()


if __name__ == '__main__':
    demo_run(turns=4, seed=42)
