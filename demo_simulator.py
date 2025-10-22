"""Small demo simulator that uses `reference_card_decks` to show one AI turn.

This script is intentionally lightweight and demonstrates how a simulator
could draw a deployment card, pick a tactic, and draw an action card without
mutating the original reference decks.
"""

import random
from reference_card_decks import (
    battleplan_deck,
    battle_tactic_deck,
    tactic_to_actions,
    objective_action_deck,
)


def draw_one(items):
    """Return a random element from a list (non-destructive)."""
    return random.choice(items) if items else None


def simulate_turn(seed=None):
    if seed is not None:
        random.seed(seed)

    print("--- Demo AI Turn ---")

    deployment = draw_one(battleplan_deck)
    print(f"Deployment card: {deployment['title']}")
    print(f"  -> {deployment.get('deployment','(no deployment text)')}\n")

    tactic = draw_one(battle_tactic_deck)
    print(f"Battle Tactic: {tactic['title']}")
    print(f"  -> {tactic.get('description','')}")

    action_deck = tactic_to_actions.get(tactic['title'], [])
    # also mix in one objective action randomly to show mixing behaviour
    combined = list(action_deck)
    if objective_action_deck:
        combined.append(random.choice(objective_action_deck))

    action = draw_one(combined)
    if action:
        print(f"\nAction drawn: {action.get('title','(unnamed)')}")
        print(f"  -> {action.get('behavior','')}")
    else:
        print("\nNo action available for this tactic.")


if __name__ == '__main__':
    simulate_turn(seed=42)
