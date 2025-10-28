import random

# --- General's Handbook 2021 Data ---
# These are the 8 Battle Tactics from GHB 2021.
# The AI will draw one of these each turn.
ghb_2021_battle_tactics = [
    "Broken Ranks",
    "Conquer",
    "Slay the Warlord",
    "Ferocious Advance",
    "Savage Spearhead",
    "Aggressive Expansion",
    "Monstrous Takeover",
    "Bring It Down"
]

# --- Deck 1: Battleplan Deployment Deck (12 Cards) ---
# This deck determines where the AI places its units.
# I have created 12 logical placement cards.
deployment_deck = [
    "DEPLOYMENT CARD 1: Place one Battleline unit on an objective in your territory.",
    "DEPLOYMENT CARD 2: Place one Battleline unit on an objective in neutral territory.",
    "DEPLOYMENT CARD 3: Place your General as far forward as possible, centrally.",
    "DEPLOYMENT CARD 4: Place a MONSTER on one flank.",
    "DEPLOYMENT CARD 5: Place a unit with 10+ models on the other flank.",
    "DEPLOYMENT CARD 6: Place your strongest melee unit in ambush (or in reserve).",
    "DEPLOYMENT CARD 7: Place a fast unit (cavalry/flier) in a position to threaten a flank.",
    "DEPLOYMENT CARD 8: Place a shooting unit in your territory with a good line of sight.",
    "DEPLOYMENT CARD 9: Place a Battleline unit defensively, screening your backline.",
    "DEPLOYMENT CARD 10: Place your toughest (high save/wounds) unit in the center.",
    "DEPLOYMENT CARD 11: Place a support Hero (e.g., Warchanter) near your General.",
    "DEPLOYMENT CARD 12: Place all remaining units aggressively, 3\" behind your front line."
]

# --- Decks 2 & 3: Battle Tactic & Action Decks ---
# This is the core of the Woehammer system.
# We first draw a TACTIC, then draw ACTIONS from that tactic's deck.

# We need to create an 8-card "Action Deck" for EACH of the 8 tactics.
# I will create the deck for "Monstrous Takeover" as an example.
# These actions are written for "Aggressive" Orruk Warclans.

action_deck_monstrous_takeover = [
    "MONSTER Unit: Charge the closest enemy unit. Fight first.",
    "MONSTER Unit: Move towards the closest objective not in your control. If in range, charge.",
    "MELEE Unit: Move towards the closest friendly MONSTER. Charge any unit threatening it.",
    "MELEE Unit: Run towards the closest objective. Do not charge.",
    "SHOOTING Unit: Target the enemy unit closest to an objective.",
    "ANY Unit: Move towards the closest enemy MONSTER. Charge if in range.",
    "ANY Unit: Run towards the center of the board. Stay more than 9\" from the enemy.",
    "GENERAL: Use its Command Ability on the closest friendly MONSTER, then move with it."
]

# --- !! ACTION REQUIRED !! ---
# You will need to create the 8-card decks for the other 7 tactics.
# I am creating empty lists as placeholders.
action_deck_broken_ranks = ["(Placeholder: Add 8 'Broken Ranks' actions)"]
action_deck_conquer = ["(Placeholder: Add 8 'Conquer' actions)"]
action_deck_slay_the_warlord = ["(Placeholder: Add 8 'Slay the Warlord' actions)"]
action_deck_ferocious_advance = ["(Placeholder: Add 8 'Ferocious Advance' actions)"]
action_deck_savage_spearhead = ["(Placeholder: Add 8 'Savage Spearhead' actions)"]
action_deck_aggressive_expansion = ["(Placeholder: Add 8 'Aggressive Expansion' actions)"]
action_deck_bring_it_down = ["(Placeholder: Add 8 'Bring It Down' actions)"]

# This dictionary links the Tactic Name to its corresponding Action Deck
ACTION_DECKS = {
    "Broken Ranks": action_deck_broken_ranks,
    "Conquer": action_deck_conquer,
    "Slay the Warlord": action_deck_slay_the_warlord,
    "Ferocious Advance": action_deck_ferocious_advance,
    "Savage Spearhead": action_deck_savage_spearhead,
    "Aggressive Expansion": action_deck_aggressive_expansion,
    "Monstrous Takeover": action_deck_monstrous_takeover,
    "Bring It Down": action_deck_bring_it_down
}

# --- The Script's Function ---

def draw_solo_warhammer_cards():
    """
    Simulates a turn for the Solo AI player.
    1. Draws one Deployment Card.
    2. Draws one AI Battle Tactic for the turn.
    3. Draws one Action Card from that tactic's specific deck.
    """
    
    # Shuffle the decks before drawing
    random.shuffle(deployment_deck)
    random.shuffle(ghb_2021_battle_tactics)
    
    # 1. Draw from Deployment Deck
    # (In a real game, you'd do this once per unit at the start)
    print("--- AI DEPLOYMENT DRAW ---")
    drawn_deployment = deployment_deck.pop()
    print(f"Deployment Instruction: {drawn_deployment}\n")
    
    # 2. Draw the AI's Battle Tactic for the turn
    print("--- AI BATTLE TACTIC DRAW ---")
    drawn_tactic = ghb_2021_battle_tactics[0] # Just peek at the top card
    print(f"AI Battle Tactic for this turn: {drawn_tactic}\n")
    
    # 3. Draw an Action Card from the corresponding deck
    print("--- AI ACTION CARD DRAW ---")
    # Get the correct 8-card deck based on the tactic
    current_action_deck = ACTION_DECKS.get(drawn_tactic)
    
    if current_action_deck:
        # Shuffle the chosen action deck
        random.shuffle(current_action_deck)
        drawn_action = current_action_deck.pop()
        print(f"Action Instruction: {drawn_action}\n")
    else:
        print(f"ERROR: No Action Deck found for {drawn_tactic}\n")

# --- Run the Simulation ---
if __name__ == "__main__":
    draw_solo_warhammer_cards()
    print("--- End of Draw ---")
    print(f"Remember to fill in the placeholder Action Decks in the script!")