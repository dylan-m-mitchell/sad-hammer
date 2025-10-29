"""Full solo AI simulator for Age of Sigmar (card-driven)

This module implements the simulator behavior using the data in
`reference_card_decks.py`. It is standalone and does not modify other
project files. The simulator follows the rules described on the Woehammer
blog and the General's Handbook 2021 conventions where applicable.
"""

import random
from typing import List, Dict, Optional

# reference_card_decks imported by other modules; avoid unused-import warnings here
from backend.deck_manager import TacticsDeckManager, create_turn_action_assignments


# Aggression execution modifiers - all units always act, but aggression affects HOW they execute
# These modifiers influence tactical decision-making (charge ranges, movement preferences, target priorities)
AGGRESSION_EXECUTION_MODIFIERS = {
    "Aggressive": {
        "charge_range_threshold": 12,  # Willing to attempt longer charges
        "run_preference": 0.7,  # 70% chance to Run vs Move when closing distance
        "retreat_threshold": 0.25,  # Only retreat if below 25% effective strength
        "target_priority": "highest_threat",  # Target most dangerous enemy
    },
    "Neutral": {
        "charge_range_threshold": 9,
        "run_preference": 0.5,
        "retreat_threshold": 0.4,
        "target_priority": "balanced",
    },
    "Cautious": {
        "charge_range_threshold": 6,  # Only charge if very close
        "run_preference": 0.2,  # Prefer normal Move over Run
        "retreat_threshold": 0.6,  # Retreat earlier for safety
        "target_priority": "lowest_risk",
    },
}

# Legacy constant kept for backward compatibility (deprecated - no longer used)
AGGRESSION_CHECK_TARGET = {
    "Aggressive": 3,
    "Neutral": 4,
    "Cautious": 5,
}


class Unit:
    def __init__(
        self,
        name: str,
        aggression: str = "Neutral",
        keywords: Optional[List[str]] = None,
        aggression_modifier: int = 0,
    ):
        self.name = name
        self.aggression = aggression
        self.keywords = keywords or []
        # numeric modifier added to the d6 roll for aggression checks (can be negative)
        self.aggression_modifier = int(aggression_modifier or 0)

    def __repr__(self):
        return (
            f"Unit(name={self.name!r}, aggression={self.aggression!r}, keywords={self.keywords!r})"
        )


class SoloSimulator:
    def __init__(
        self,
        units: List[Unit],
        seed: Optional[int] = None,
        aggression_thresholds: Optional[Dict[str, int]] = None,
    ):
        self.units = units
        self.turn = 1
        self.seed = seed
        # use an instance RNG so we don't alter global random state
        self.rng = random.Random(seed)

        # allow callers to override aggression thresholds for experimentation or tests
        self.aggression_targets = aggression_thresholds or AGGRESSION_CHECK_TARGET

        # Initialize Battle Tactics Deck Manager
        self.tactics_deck = TacticsDeckManager(rng=self.rng, current_turn=self.turn)

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
        modifier = int(getattr(unit, "aggression_modifier", 0) or 0)
        total = roll + modifier
        result = total >= target
        return {
            "result": result,
            "roll": roll,
            "modifier": modifier,
            "total": total,
            "target": target,
        }

    def choose_battle_tactic(self) -> Optional[Dict]:
        """Draw a Battle Tactic card from the managed deck.

        Returns the full tactic dict (with title, description, etc.) or None if empty.
        This method is now a thin wrapper around TacticsDeckManager.
        """
        tactic_card = self.tactics_deck.draw_tactic()
        return tactic_card

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

        # Advance the tactics deck turn counter
        self.tactics_deck.advance_turn(self.turn)

        # Draw a Battle Tactic card
        tactic_card = self.choose_battle_tactic()
        if tactic_card is None:
            log.append({"event": "no_tactic_available"})
            self.turn += 1
            return log

        tactic_title = tactic_card["title"]

        # Log the battle tactic so players know the AI's goal
        log.append({
            "event": "battle_tactic_drawn",
            "tactic": tactic_title,
            "description": tactic_card.get("description", ""),
        })

        # Log aggression levels for each unit (informational only)
        # All units act - aggression affects HOW they execute their actions
        for u in self.units:
            modifiers = AGGRESSION_EXECUTION_MODIFIERS.get(
                u.aggression, AGGRESSION_EXECUTION_MODIFIERS["Neutral"]
            )
            log.append(
                {
                    "event": "aggression_level",
                    "unit": u.name,
                    "aggression": u.aggression,
                    "modifiers": modifiers,
                }
            )

        # All units act (no gating)
        aggression_results = {u.name: True for u in self.units}

        # Use deck manager to create action assignments sorted by initiative
        action_assignments = create_turn_action_assignments(
            tactic_card, self.units, aggression_results, rng=self.rng
        )

        # Resolve actions in initiative order (already sorted by create_turn_action_assignments)
        for assignment in action_assignments:
            rec = {
                "turn": self.turn,
                "tactic": tactic_title,
                "unit": assignment["unit"],
                "card_title": assignment["card_title"],
                "initiative": assignment["initiative"],
                "behavior": assignment["behavior"],
            }
            # Simple textual resolution: append to log
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


if __name__ == "__main__":
    demo_run(turns=4, seed=42)
