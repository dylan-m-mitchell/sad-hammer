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
    {"id": 1, "title": "Border War (2016)", "deployment": "4 objectives: hold your own=1, border objectives=2, opponent's objective=5; cap 6 points plus tactic. Play prudently; don't overextend.", "twist": "Underdog +1 to hit if they charged this turn."},
    {"id": 2, "title": "Focal Points (2018)", "deployment": "Capture objectives across the central cross: Home and Flank objectives with one/two/more scoring and extra for holding a cross. Choose between wide flank grabs or pushing into opponent Home.", "twist": "Underdog can change the central objective to Home or Flank to consolidate scoring."},
    {"id": 3, "title": "Starstrike (2019)", "deployment": "Fewer landing lanes; objectives that would be on terrain become that terrain piece. Simpler scoring: 3 points per objective and 3 for holding more than opponent.", "twist": "—"},
    {"id": 4, "title": "Shifting Objectives (2020)", "deployment": "Large open map; each round the active player sets which objective is worth 2 points, others worth 1; controlling more objectives gives +2. Suggested terrain: obscuring and place of power per side.", "twist": "Underdog can force the active player to reroll the die that selects the primary objective."},
    {"id": 5, "title": "Feral Foray (2021)", "deployment": "Six objectives, straightforward scoring. Incentivizes raiding and scouting; the twist rewards attacking and clever play.", "twist": "At start of round players may raid an enemy objective they control; underdog may raid a contested enemy objective."},
    {"id": 6, "title": "The Jaws of Gallet", "deployment": "Five objectives, Hold One/Two/More scoring. After turn 1 objectives begin to collapse (one removed each turn).", "twist": "Starting on round 2 the Underdog may pick an objective to pull if they wish."},
    {"id": 7, "title": "Battle for the Pass (2017)", "deployment": "Similar scoring to Border War (hold your own=1, border=2, opponent's=5) but uses a short-edge deployment so armies hike sooner into the field.", "twist": "+2 to control score for non-hero units (encourages smaller forces to push up)."},
    {"id": 8, "title": "Scorched Earth (2019)", "deployment": "Standard Hold One/Two/More scoring with a modified deployment (long/short edges may differ); focuses on denying opponent opportunities.", "twist": "Underdog can pick one objective in their territory and treat enemy control score as 5 less for that objective."},
    {"id": 9, "title": "The Better Part of Valour (2020)", "deployment": "Six objectives, scoring similar to other six-objective maps. Unique mechanic: non-hero kills on objectives can gain Dominant status and boost control score.", "twist": "Underdog gains +1 to hit against Dominant units."},
    {"id": 10, "title": "The Vice (2021)", "deployment": "Long-edge deployment drawing players to the centre; objectives shift through the game with new objectives appearing on later rounds.", "twist": "Underdog can inflict D3 mortal damage on units contesting a selected objective at end of their turn; objectives are moved/removed on later rounds."},
    {"id": 11, "title": "Close to the Chest (2022-2023 S2)", "deployment": "Small neutral territory; hold 1/2 scoring with a designated primary objective worth more. The none-active player picks the primary objective each round.", "twist": "Underdog can roll to force the opponent to pick a different primary objective on a 5+."},
    {"id": 12, "title": "Limited Resources (2023)", "deployment": "Hold One/Two/More scoring; extracting resources can prevent a player from controlling an objective on later turns.", "twist": "Underdog can add +3 to control scores for friendly units contesting an objective from which they are extracting resources."},
]


# ----------------------
# Battle Tactic deck (8 cards)
# ----------------------
# The blog references a set of battle tactic cards. Each battle tactic has:
# - title: The name of the tactic
# - description: What the tactic focuses on
# - enters_deck_on_turn: Which turn this card is added to the tactics deck
#   (0 = in deck from start, 1 = added after turn 1, etc.)
# - designated_units: How to choose which unit(s) this tactic applies to
# - designated_objectives: How to choose which objective(s) this tactic applies to
#
# The Tactics Deck is shuffled at the start of the game (with cards that have
# enters_deck_on_turn=0), then one card is drawn each turn. When a card is drawn,
# it is discarded from the deck. Cards with enters_deck_on_turn > 0 are added
# to the discard pile at the appropriate time, then all discarded cards are
# reshuffled back into the deck when it runs out.
battle_tactic_deck = [
    {
        "title": "Monstrous Takeover",
        "description": "Prioritize monstrous units to seize objectives.",
        "enters_deck_on_turn": 0,  # In deck from start
        "designated_units": "All units with Monster keyword; if multiple, choose closest to nearest objective.",
        "designated_objectives": "Nearest objective to designated monster(s)."
    },
    {
        "title": "Ferocious Advance", 
        "description": "Aggressive repositioning and charges.",
        "enters_deck_on_turn": 0,  # In deck from start
        "designated_units": "Hero with highest move characteristic; if tied, closest to enemy.",
        "designated_objectives": "Objective closest to designated hero."
    },
    {
        "title": "Aggressive Expansion",
        "description": "Move multiple units toward objectives to contest or capture.",
        "enters_deck_on_turn": 0,  # In deck from start
        "designated_units": "All units within 18\" of any objective.",
        "designated_objectives": "All objectives not currently controlled by AI."
    },
    {
        "title": "Conquer",
        "description": "Focus on taking and holding objectives.",
        "enters_deck_on_turn": 0,  # In deck from start
        "designated_units": "All Battleline units.",
        "designated_objectives": "Two closest objectives to AI deployment zone."
    },
    {
        "title": "Broken Ranks",
        "description": "A versatile tactic that breaks enemy formations.",
        "enters_deck_on_turn": 2,  # Added to deck after turn 1 completes (drawn starting turn 2)
        "designated_units": "All units; priority to fastest units first.",
        "designated_objectives": "Center objective or objective closest to enemy Battleline."
    },
    {
        "title": "Bring It Down",
        "description": "Target a specific enemy unit to be destroyed.",
        "enters_deck_on_turn": 0,  # In deck from start
        "designated_units": "All units that can shoot or fight; prioritize units with highest attack count.",
        "designated_objectives": "None; focus is on destroying designated enemy unit (highest wounds or points value)."
    },
    {
        "title": "Slay the Warlord",
        "description": "Kill the enemy commander/leader.",
        "enters_deck_on_turn": 0,  # In deck from start
        "designated_units": "All units; priority to units with high damage output.",
        "designated_objectives": "None; focus is on eliminating enemy general/leader (if dead, next highest-cost enemy)."
    },
    {
        "title": "Savage Spearhead",
        "description": "Push a concentrated spearhead forward to overwhelm a flank.",
        "enters_deck_on_turn": 0,  # In deck from start
        "designated_units": "Three fastest units or units on one flank (left or right, whichever has more units).",
        "designated_objectives": "Flank objective on the same side as designated units."
    },
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

# ----------------------
# Objective Action Cards (4 cards)
# ----------------------
# These 4 cards are shuffled together with the 8 tactic-specific action cards
# each turn to create a 12-card Action Deck. Each card specifies general
# objective-focused behavior. Initiative numbers are included to ensure proper
# sorting when drawn.
objective_action_deck = [
    {"title": "Contest Objective", "behavior": "If within 6\" of an objective, move to contest it rather than charging enemies. If already contesting, hold position.", "initiative": 9},
    {"title": "Capture Objective", "behavior": "Move to the nearest objective not controlled by the AI. If already there, secure it by removing enemy models.", "initiative": 10},
    {"title": "Deny Objective", "behavior": "Move toward an enemy-controlled objective and attempt to contest it. Priority is denying enemy points, not securing it yourself.", "initiative": 11},
    {"title": "Secure Objective", "behavior": "If within 3\" of an objective, remain there and defend it. Attack any enemy units that come within 3\".", "initiative": 12},
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
