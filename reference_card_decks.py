"""Reference card decks for Solo Wargaming (data-only)

This file contains three decks used by Peter Holland's Solo Wargaming system
as described on the Woehammer blog (Oct-Nov 2021). The intent is to provide
data only (card text and minimal metadata) that matches the blog examples
and the Age of Sigmar General's Handbook 2021 rules where relevant.

This is a standalone reference module. It intentionally does not modify
`solo_wargaming_ai.py` so it can be used as a stable data source.

Assumptions / notes:
- Battleplan deck contains 12 cards; where the blog does not specify exact
  deployment text, reasonable inferred deployment instructions are used.
- There are 8 Battle Tactic cards (the blog references many tactics; we've
  selected the named ones and included 'Broken Ranks' as used in the blog).
- Each tactic has an associated list of action cards. The blog provides the
  full set for the 'Broken Ranks' deck; for other tactics we include placeholders
  or short inferred actions which can be expanded later.
- Objective action cards are a small set taken/inferred from the blog images
  and descriptions.
"""

import random

# ----------------------
# Battleplan deck (12 cards)
# ----------------------
# The blog mentions a 'cover card' that explains deployment and a number of
# deployment cards. We provide 12 cards with deployment hints.
battleplan_deck = [
    {"id": 1, "title": "Cover: Standard Deployment", "deployment": "Follow cover card layout; place objectives as shown; deploy card-controlled units as specified."},
    {"id": 2, "title": "Deploy: Right Flank", "deployment": "Place majority of card-controlled units on the right flank within 6\" of table edge; light screen in centre."},
    {"id": 3, "title": "Deploy: Left Flank", "deployment": "Place majority of card-controlled units on the left flank within 6\" of table edge; light screen in centre."},
    {"id": 4, "title": "Deploy: Balanced", "deployment": "Split forces evenly across left, centre and right — deploy battleline evenly."},
    {"id": 5, "title": "Deploy: Clumped Centre", "deployment": "Concentrate forces toward centre objective; place one heavy unit guarding centre."},
    {"id": 6, "title": "Deploy: Forward Push", "deployment": "Deploy most units forward, within 9\" of centre line to encourage early engagement."},
    {"id": 7, "title": "Deploy: Defensive Line", "deployment": "Deploy units in a defensive line across centre; place monsters to anchor flanks."},
    {"id": 8, "title": "Deploy: Ambush", "deployment": "Deploy small units forward and keep heavy units in reserve behind terrain features."},
    {"id": 9, "title": "Deploy: Objective Hold", "deployment": "Place one unit directly on the centre objective if possible; rest arrayed to defend."},
    {"id": 10, "title": "Deploy: Scattered", "deployment": "Distribute units across table to contest multiple objectives."},
    {"id": 11, "title": "Deploy: Strong Left", "deployment": "Heavy concentration on left with a token force on right."},
    {"id": 12, "title": "Deploy: Strong Right", "deployment": "Heavy concentration on right with a token force on left."},
]


# ----------------------
# Battle Tactic deck (8 cards)
# ----------------------
# The blog references a set of battle tactic cards. We'll include the named
# ones and a few common tactics used in the posts. Each tactic entry includes
# a short rule for selection/usage (how it is added/removed from the tactic
# pool across turns) to help any simulator implementation.
battle_tactic_deck = [
    {"title": "Monstrous Takeover", "description": "Prioritize monstrous units to seize objectives; designate target monster if multiple.", "usage": "Start in pool; when drawn discard; other tactics added per rules."},
    {"title": "Ferocious Advance", "description": "Aggressive repositioning and charges: select a hero/unit to lead the advance.", "usage": "Start in pool; when drawn discard."},
    {"title": "Aggressive Expansion", "description": "Attempt to move multiple units toward objectives to contest or capture.", "usage": "Start in pool; when drawn discard."},
    {"title": "Conquer", "description": "Focus on taking and holding objectives; select two objectives as priority.", "usage": "Start in pool; when drawn discard."},
    {"title": "Broken Ranks", "description": "A versatile tactic used by several examples on the blog; its action deck is provided separately.", "usage": "Added into the tactic pool after turn 1 (per blog)."},
    {"title": "Bring It Down", "description": "Target a specific enemy unit to be destroyed; designate nearest high-value target.", "usage": "Start in pool; when drawn discard."},
    {"title": "Slay the Warlord", "description": "Prioritise killing the enemy commander/leader; if impossible, pick the next highest-cost enemy model.", "usage": "Start in pool; when drawn discard."},
    {"title": "Savage Spearhead", "description": "Push a concentrated spearhead forward to overwhelm a flank and seize objectives.", "usage": "Start in pool; when drawn discard."},
]


# ----------------------
# Action decks
# ----------------------
# The blog shows the Broken Ranks action cards explicitly; we'll include those
# verbatim (as used in your original file). For other tactics we'll include
# short inferred actions so the data set is complete.

broken_ranks_actions = [
    {"title": "WAAAGH! Forward!", "behavior": "If not within 12\" of an enemy, Run toward the nearest visible enemy unit. If within 12\", Move normally to close the gap and prepare to charge next turn.", "initiative": 8},
    {"title": "Smash da Weakest!", "behavior": "Identify the nearest Battleline enemy unit. Move toward it and attempt a Charge if within range. If engaged, Pile In and Attack.", "initiative": 7},
    {"title": "Break Their Line!", "behavior": "Select the enemy Battleline unit closest to the center objective. Move toward that unit, ignoring other distractions. If engaged, Attack until destroyed or unit dies.", "initiative": 6},
    {"title": "Reposition fer da Kill!", "behavior": "If not in combat, move toward the nearest flank of an enemy Battleline. If within 3\", Retreat 6\" toward cover, then attempt to Charge a different target next turn.", "initiative": 5},
    {"title": "Da Boss Wants Blood!", "behavior": "Prioritize the enemy Hero closest to a Battleline unit. Move toward that Hero, only Charge if the Battleline unit can also be caught within 3\". If engaged, Attack the Hero.", "initiative": 4},
    {"title": "Trample Dem Flat!", "behavior": "If this unit has the Monster keyword, perform a Monstrous Rampage if eligible. Then Attack the nearest Battleline unit or Move toward nearest enemy objective if none remain.", "initiative": 3},
    {"title": "Keep Krumpin'!", "behavior": "If in melee, always Attack. If not, Advance toward the nearest ongoing combat to assist friendly units. If within 3\", Pile In.", "initiative": 2},
    {"title": "WAAAGH's Endin' Soon!", "behavior": "If within 12\" of an objective, Move to capture it even if enemy units are present. Otherwise, Run toward the largest cluster of enemy models visible.", "initiative": 1},
]

# Minimal action decks for other named tactics (placeholders/inferred actions)
monstrous_takeover_actions = [
    {"title": "Rampage Breaker", "behavior": "Monsters push forward to seize objectives; attempt to charge if within 6\".", "initiative": 8},
    {"title": "Monster Anchor", "behavior": "Monster holds a flank and refuses to fall back; other units support.", "initiative": 7},
    {"title": "Devour the Weak", "behavior": "Designated monster moves to the nearest low-toughness unit and attacks aggressively.", "initiative": 6},
    {"title": "Thunderous Charge", "behavior": "If within charge range, monster charges and attacks highest-priority target.", "initiative": 5},
    {"title": "Relentless Advance", "behavior": "Monsters advance toward the nearest objective and contest if possible.", "initiative": 4},
    {"title": "Orbital Roar", "behavior": "Monster performs an intimidating action to reduce enemy morale in 6\".", "initiative": 3},
    {"title": "Feeding Frenzy", "behavior": "If monster destroys a unit, it continues to the next nearest enemy unit within move distance.", "initiative": 2},
    {"title": "Anchor & Hold", "behavior": "Monster secures an objective and refuses to move unless overwhelmed.", "initiative": 1},
]

ferocious_advance_actions = [
    {"title": "Ferocious Lead", "behavior": "Designated unit runs and charges if possible; supporting units advance toward nearest combat.", "initiative": 8},
    {"title": "Hammer & Anvil", "behavior": "Two units coordinate: one fixes while the other attempts to charge from flank.", "initiative": 7},
    {"title": "Bounding Advance", "behavior": "Units run in bounds to close distance rapidly, avoiding disengagement if possible.", "initiative": 6},
    {"title": "Shock Troops", "behavior": "Prioritise charging enemy Battleline units near objectives.", "initiative": 5},
    {"title": "Press Home", "behavior": "If an enemy unit is isolated, the AI attempts to overwhelm it with multiple charges.", "initiative": 4},
    {"title": "Flank & Roll", "behavior": "Designated unit attempts to outflank and attack the enemy's softer side.", "initiative": 3},
    {"title": "Take Ground", "behavior": "If not in combat, advance toward the nearest contested objective.", "initiative": 2},
    {"title": "Rescind", "behavior": "If severely outnumbered, unit falls back 6\" toward friendly cover, then hold.", "initiative": 1},
]

aggressive_expansion_actions = [
    {"title": "Push for Objectives", "behavior": "Units attempt to reach priority objectives and contest them.", "initiative": 8},
    {"title": "Wide Sweep", "behavior": "Spread forces to threaten multiple objectives simultaneously.", "initiative": 7},
    {"title": "Shock & Seize", "behavior": "Concentrate attacks on objective defenders to clear the way.", "initiative": 6},
    {"title": "Fast Strike", "behavior": "Fast units run and attempt to take objectives early in the turn.", "initiative": 5},
    {"title": "Hold & Trade", "behavior": "If contested, units trade wounds to deny enemy easy captures.", "initiative": 4},
    {"title": "Secure Flanks", "behavior": "Assign one unit to hold each flank to prevent enemy encirclement.", "initiative": 3},
    {"title": "Suppressive Fire", "behavior": "Shooting units target models contesting objectives to enable captures.", "initiative": 2},
    {"title": "Consolidate", "behavior": "After moving, units consolidate to defend captured objectives.", "initiative": 1},
]

conquer_actions = [
    {"title": "Secure and Hold", "behavior": "Move to capture objectives; lower priority to engage unless contested.", "initiative": 8},
    {"title": "Defensive Perimeter", "behavior": "After capturing, form a perimeter to deny enemy re-capture.", "initiative": 7},
    {"title": "Reinforce Point", "behavior": "Send supporting units to any newly captured objective.", "initiative": 6},
    {"title": "Consolidate Ranks", "behavior": "If a capture occurred this turn, units brace and refuse charges where possible.", "initiative": 5},
    {"title": "Counter-Push", "behavior": "If an enemy assaults a captured objective, respond with a focused counter-attack.", "initiative": 4},
    {"title": "Objective Pivot", "behavior": "If primary objective is lost, swap to nearest uncontested objective.", "initiative": 3},
    {"title": "Hold Ground", "behavior": "Units on objectives hold and contest; allied units assist as needed.", "initiative": 2},
    {"title": "Fallback Plan", "behavior": "If overrun, withdraw to last defensible objective and regroup.", "initiative": 1},
]

bring_it_down_actions = [
    {"title": "Targeted Strike", "behavior": "Concentrate attacks on the designated target; supporting units focus fire.", "initiative": 8},
    {"title": "Precision Assault", "behavior": "Designated units attempt to remove key enemy models with focused attacks.", "initiative": 7},
    {"title": "Cut the Leaders", "behavior": "If the leader is nearby, priority attacks target leadership models.", "initiative": 6},
    {"title": "Suppress the Guards", "behavior": "Eliminate or push back units protecting the designated target.", "initiative": 5},
    {"title": "Isolate Target", "behavior": "Use mobility to isolate the target from support before attacking.", "initiative": 4},
    {"title": "Overwhelm", "behavior": "Call in multiple units to finish off the target quickly.", "initiative": 3},
    {"title": "Finish the Job", "behavior": "If the target is wounded, units concentrate to ensure elimination.", "initiative": 2},
    {"title": "Celebrate Victory", "behavior": "After elimination, units push to next nearest objective.", "initiative": 1},
]

slay_the_warlord_actions = [
    {"title": "Kill the Commander", "behavior": "Designated units attempt to close on enemy leader and attack; if leader is dead, pick new highest-value target.", "initiative": 8},
    {"title": "Leader Hunt", "behavior": "Use scouting units to locate the leader and report back; then strike.", "initiative": 7},
    {"title": "Feint & Strike", "behavior": "Feint to draw defenders, then send a unit to attack the leader.", "initiative": 6},
    {"title": "Split the Guard", "behavior": "Force the leader's guards to split, then target the leader when exposed.", "initiative": 5},
    {"title": "Snipe Opportunity", "behavior": "Ranged units target the leader if he becomes isolated.", "initiative": 4},
    {"title": "Disrupt", "behavior": "Attack support units to reduce leader's protection before closing.", "initiative": 3},
    {"title": "Final Blow", "behavior": "All available units focus on the leader once wounded sufficiently.", "initiative": 2},
    {"title": "Fallback Target", "behavior": "If the leader is unreachable, pick the next most valuable target and execute.", "initiative": 1},
]

hold_the_line_actions = [
    {"title": "Brace", "behavior": "Units refuse charges where possible; contest objectives and remain near friendly units.", "initiative": 8},
    {"title": "Anchor", "behavior": "Designated units hold position and force enemy to come to them.", "initiative": 7},
    {"title": "Trade Favourably", "behavior": "If attacked, accept combat if it secures objective or reduces enemy capability.", "initiative": 6},
    {"title": "Reinforce the Line", "behavior": "Bring supporting units to threatened objectives or gaps.", "initiative": 5},
    {"title": "Deny Passage", "behavior": "Use terrain to block enemy movement and protect objectives.", "initiative": 4},
    {"title": "Counter Punch", "behavior": "If an enemy overextends, counterattack with nearby reserves.", "initiative": 3},
    {"title": "Hold Fast", "behavior": "Units refuse to move off objectives unless ordered or destroyed.", "initiative": 2},
    {"title": "Orderly Retreat", "behavior": "If overwhelmed, withdraw to the next objective in order and regroup.", "initiative": 1},
]

# Objective action cards (a small set inferred from the blog)
objective_action_deck = [
    {"title": "Contest Objective", "behavior": "If within 6\" of objective, attempt to contest rather than charge."},
    {"title": "Capture Objective", "behavior": "Move to capture nearest friendly-controlled objective."},
    {"title": "Deny Objective", "behavior": "Prevent enemy from holding objective: attempt to contest if possible."},
    {"title": "Ignore Objective", "behavior": "Prioritize combat over objective unless within 3\"."},
]


# map tactic title -> action deck (reference lookup)
tactic_to_actions = {
    "Broken Ranks": broken_ranks_actions,
    "Monstrous Takeover": monstrous_takeover_actions,
    "Ferocious Advance": ferocious_advance_actions,
    "Aggressive Expansion": aggressive_expansion_actions,
    "Conquer": conquer_actions,
    "Bring It Down": bring_it_down_actions,
    "Slay the Warlord": slay_the_warlord_actions,
    "Savage Spearhead": hold_the_line_actions,
}


def sample_print():
    """Print sample info to verify the module loads and decks are usable."""
    print("Battleplan cards:", len(battleplan_deck))
    print("Tactic cards:", len(battle_tactic_deck))
    print("Broken Ranks actions:", len(broken_ranks_actions))
    print("Objective action cards:", len(objective_action_deck))
    print("-- sample battleplan --")
    print(battleplan_deck[0])
    print("-- sample tactic --")
    print(battle_tactic_deck[0])
    print("-- sample broken ranks card --")
    print(broken_ranks_actions[0])


if __name__ == '__main__':
    sample_print()
