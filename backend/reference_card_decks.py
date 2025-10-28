"""Reference card decks for Solo Wargaming (data-only)

Copied into backend package for server ownership.
"""

import random

# Battleplan deck (12 cards)
battleplan_deck = [
    {"id": 1, "title": "First Blood (2021)", "deployment": "Early engagement across the line; pressure forward and threaten enemy-half objectives.", "twist": "—"},
    {"id": 2, "title": "Power Struggle (2021)", "deployment": "Objectives form a central axis; contest center and paired flanks.", "twist": "—"},
    {"id": 3, "title": "Savage Gains (2021)", "deployment": "Reward for taking enemy territory; push forward early to score.", "twist": "—"},
    {"id": 4, "title": "Apex Predators (2021)", "deployment": "Leaders capture; protect heroes while anchoring the center.", "twist": "—"},
    {"id": 5, "title": "Survival of the Fittest (2021)", "deployment": "Predator/prey mechanics influence scoring; stay flexible across the board.", "twist": "—"},
    {"id": 6, "title": "Marking Territory (2021)", "deployment": "Consolidate and hold key objectives; defensive posture rewarded.", "twist": "—"},
    {"id": 7, "title": "Feral Foray (2021)", "deployment": "Raiding mechanics; aggressive objective tagging and retreats.", "twist": "—"},
    {"id": 8, "title": "The Vice (2021)", "deployment": "Objectives collapse toward center later; set up to pivot.", "twist": "—"},
    {"id": 9, "title": "Tectonic Interference (2021)", "deployment": "Shifting primaries; adapt and reallocate swiftly.", "twist": "—"},
    {"id": 10, "title": "Tooth and Nail (2021)", "deployment": "Straight fight, limited reserves; press the line.", "twist": "—"},
    {"id": 11, "title": "Power in Numbers (2021)", "deployment": "Model count/holding emphasis; spread to control.", "twist": "—"},
    {"id": 12, "title": "Veins of Ghur (2021)", "deployment": "Falling objectives; be ready to flex to new drops.", "twist": "—"},
]

# Battle Tactic deck (8 cards)
battle_tactic_deck = [
    {
        "title": "Monstrous Takeover",
        "description": "Prioritize monstrous units to seize objectives.",
        "enters_deck_on_turn": 0,
        "designated_units_raw": "All units with Monster keyword; if multiple, choose closest to nearest objective.",
        # sanitized fallback: spatial instructions are not supported by the simulator (card-only model)
        "designated_units": "monster random",
        "designated_objectives": "Nearest objective to designated monster(s)."
    },
    {
        "title": "Ferocious Advance",
        "description": "Aggressive repositioning and charges.",
        "enters_deck_on_turn": 0,
        "designated_units_raw": "Hero with highest move characteristic; if tied, closest to enemy.",
        # fallback: interpret spatial tie-breaks as deterministic random among highest-move heroes
        "designated_units": "hero random",
        "designated_objectives": "Objective closest to designated hero."
    },
    {
        "title": "Aggressive Expansion",
        "description": "Move multiple units toward objectives to contest or capture.",
        "enters_deck_on_turn": 0,
        "designated_units_raw": "All units within 18\" of any objective.",
        # fallback: spatial filter -> attribute-only (all units), rely on RNG to pick among them
        "designated_units": "all random",
        "designated_objectives": "All objectives not currently controlled by AI."
    },
    {
        "title": "Conquer",
        "description": "Focus on taking and holding objectives.",
        "enters_deck_on_turn": 0,
        "designated_units_raw": "All Battleline units.",
        "designated_units": "battleline",
        "designated_objectives": "Two closest objectives to AI deployment zone."
    },
    {
        "title": "Broken Ranks",
        "description": "A versatile tactic that breaks enemy formations.",
        "enters_deck_on_turn": 2,
        "designated_units": "All units; priority to fastest units first.",
        "designated_objectives": "Center objective or objective closest to enemy Battleline."
    },
    {
        "title": "Bring It Down",
        "description": "Target a specific enemy unit to be destroyed.",
        "enters_deck_on_turn": 0,
        "designated_units": "All units that can shoot or fight; prioritize units with highest attack count.",
        "designated_objectives": "None; focus is on destroying designated enemy unit (highest wounds or points value)."
    },
    {
        "title": "Slay the Warlord",
        "description": "Kill the enemy commander/leader.",
        "enters_deck_on_turn": 0,
        "designated_units": "All units; priority to units with high damage output.",
        "designated_objectives": "None; focus is on eliminating enemy general/leader (if dead, next highest-cost enemy)."
    },
    {
        "title": "Savage Spearhead",
        "description": "Push a concentrated spearhead forward to overwhelm a flank.",
        "enters_deck_on_turn": 0,
        "designated_units_raw": "Three fastest units or units on one flank (left or right, whichever has more units).",
        # fallback: interpret 'fastest' as 'highest wounds' is not ideal, so default to random among units
        "designated_units": "random 3",
        "designated_objectives": "Flank objective on the same side as designated units."
    },
]

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

objective_action_deck = [
    {"title": "Contest Objective", "behavior": "If within 6\" of an objective, move to contest it rather than charging enemies. If already contesting, hold position.", "initiative": 9},
    {"title": "Capture Objective", "behavior": "Move to the nearest objective not controlled by the AI. If already there, secure it by removing enemy models.", "initiative": 10},
    {"title": "Deny Objective", "behavior": "Move toward an enemy-controlled objective and attempt to contest it. Priority is denying enemy points, not securing it yourself.", "initiative": 11},
    {"title": "Secure Objective", "behavior": "If within 3\" of an objective, remain there and defend it. Attack any enemy units that come within 3\".", "initiative": 12},
]

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
    print("Battleplan cards:", len(battleplan_deck))
    print("Tactic cards:", len(battle_tactic_deck))
    print("Broken Ranks actions:", len(broken_ranks_actions))
    print("Objective action cards:", len(objective_action_deck))


if __name__ == '__main__':
    sample_print()
