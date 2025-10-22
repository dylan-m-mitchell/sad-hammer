import random

# ----------------------
# Deck Definitions
# ----------------------

broken_ranks_deck = [
    {"title": "WAAAGH! Forward!", "behavior": "If not within 12\" of an enemy, Run toward the nearest visible enemy unit. If within 12\", Move normally to close the gap and prepare to charge next turn.", "initiative": 8},
    {"title": "Smash da Weakest!", "behavior": "Identify the nearest Battleline enemy unit. Move toward it and attempt a Charge if within range. If engaged, Pile In and Attack.", "initiative": 7},
    {"title": "Break Their Line!", "behavior": "Select the enemy Battleline unit closest to the center objective. Move toward that unit, ignoring other distractions. If engaged, Attack until destroyed or unit dies.", "initiative": 6},
    {"title": "Reposition fer da Kill!", "behavior": "If not in combat, move toward the nearest flank of an enemy Battleline. If within 3\", Retreat 6\" toward cover, then attempt to Charge a different target next turn.", "initiative": 5},
    {"title": "Da Boss Wants Blood!", "behavior": "Prioritize the enemy Hero closest to a Battleline unit. Move toward that Hero, only Charge if the Battleline unit can also be caught within 3\". If engaged, Attack the Hero.", "initiative": 4},
    {"title": "Trample Dem Flat!", "behavior": "If this unit has the Monster keyword, perform a Monstrous Rampage if eligible. Then Attack the nearest Battleline unit or Move toward nearest enemy objective if none remain.", "initiative": 3},
    {"title": "Keep Krumpin'!", "behavior": "If in melee, always Attack. If not, Advance toward the nearest ongoing combat to assist friendly units. If within 3\", Pile In.", "initiative": 2},
    {"title": "WAAAGH's Endin' Soon!", "behavior": "If within 12\" of an objective, Move to capture it even if enemy units are present. Otherwise, Run toward the largest cluster of enemy models visible.", "initiative": 1}
]

# Example for future decks
battle_tactic_deck = [
    {"title": "Broken Ranks", "action_deck": broken_ranks_deck},
    # Other tactics will be added here
]

battleplan_deck = [
    # To be filled with 12 Battleplan cards
]

objective_action_deck = [
    # To be filled with Objective Action Cards
]

# ----------------------
# Deck Functions
# ----------------------

def shuffle_deck(deck):
    """Shuffles a deck in place."""
    random.shuffle(deck)

def draw_card(deck, discard_pile=None):
    """Draws one card from the deck. Reshuffles discard pile if deck is empty."""
    if len(deck) == 0 and discard_pile:
        deck.extend(discard_pile)
        discard_pile.clear()
        shuffle_deck(deck)
    if deck:
        card = deck.pop(0)
        if discard_pile is not None:
            discard_pile.append(card)
        return card
    return None

# ----------------------
# Example Simulation
# ----------------------

def simulate_ai_turn():
    discard_pile = []
    shuffle_deck(broken_ranks_deck)
    print("AI Turn Actions (Broken Ranks):")
    for i in range(len(broken_ranks_deck)):
        card = draw_card(broken_ranks_deck, discard_pile)
        print(f"Card {i+1}: {card['title']} (Initiative {card['initiative']})")
        print(f"Behavior: {card['behavior']}\n")

# Run a simulation if script executed
if __name__ == '__main__':
    simulate_ai_turn()
