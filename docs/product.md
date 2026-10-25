# Product

_A table companion that calls the AI's moves while you measure, move and roll on
a real tabletop._

Sad Hammer is not a digital twin of the battlefield and it is not a list
builder. It is one focused app that tells you what the opposing army is trying
to do this round, in plain table language, so you can play a solo or
co-operative game with the miniatures you already own.

The old digital board game is preserved at `/digital` and the card prototype at
`/legacy`. They are not the primary experience.

## Routes

| Route | Experience |
| --- | --- |
| `/` | Table Companion — the primary experience |
| `/digital` | The board-tracking digital game, preserved on the back burner |
| `/legacy` | The original card-driven prototype, unchanged |

## Default experience

The app is playable before the player builds anything:

- The first screen is the enemy army: take the Skaven starter or import a
  roster as JSON.
- Your Stormcast starter is preloaded for the planner's hero targets, and
  either roster can be swapped, edited by hand or replaced with JSON in the
  roster editor.
- After deployment the player rolls off at the table and tells the app who has
  the first turn.
- The battle screen is one button: start the AI turn and follow it one phase at
  a time.

There is no required army, mission, points limit or difficulty choice.

## Core loop

1. Open Sad Hammer on a phone propped beside the table.
2. Confirm the enemy army, place objectives and terrain, then deploy both
   armies. The enemy guide is Press forward, Support in cover, Hold near
   objectives.
3. Roll off and tell the app who has the first turn.
4. Play your turn physically: measure, move, shoot, charge, fight and roll
   dice.
5. Press **Start the AI turn** and follow one phase at a time. Each card names
   the unit, the maneuver, the instruction and a short reason.
6. Mark any AI units you destroyed in the End phase, finish the AI turn, then
   start the next round.
7. Repeat for five battle rounds.

The app never asks for positions, distances, terrain layout, wounds or your
army's state. Every instruction is relative: "closest enemy", "within 12
inches", "if you can end in cover".

## Rosters

There are two roster slots: yours and the AI's. Either can be swapped.

- **Manual builder.** Add units and weapons, edit every field, remove what you
  do not need.
- **JSON import/export.** Copy a roster out, edit it elsewhere, paste it back.
- **Browser storage.** Both rosters and the current round state are saved in
  localStorage.
- **Starters.** Stormcast and Skaven starter profiles are available
  immediately.

A unit has: name, move, save, health, models, control, keywords and weapons
with range, attacks, hit, wound, rend and damage.

There are no points, enhancements, battleline rules or matched-play validation.
A roster only has to be structurally usable.

## AI turn planner

The planner is one stateless request: both rosters, the round, a seed and the
AI units that have been destroyed. The response is a deterministic set of phase
cards. The same round and seed always produce the same plan.

Doctrine is derived only from the unit profile:

| Type | Classification | Behaviour |
| --- | --- | --- |
| Press | Melee, non-hero units | Advance, take cover near the enemy, push an objective, charge if in range |
| Support | Ranged, non-hero units | Hold and shoot from cover, reposition for line of sight, fall back and shoot, focus the closest enemy Hero; never default to charging |
| Hold | Heroes and defensive units | Support the nearest friendly unit, hold an objective, move to cover near an objective |

Maneuvers are seeded and rotate each round using the seed and the unit ID. The
player never chooses aggression, difficulty or an AI style.

Support units have one conditional escape hatch into melee: charge only if
there is no shooting target and an enemy is already within 6 inches.

## Table UI

- Enemy army setup with the Skaven starter and JSON import.
- First-turn roll with a doctrine-based deployment hint.
- Battle screen with the round, the AI roster and one primary button: start
  the AI turn.
- The AI turn is stepped one phase at a time: Hero, Movement, Shooting, Charge,
  Combat and End. Only the current phase is shown.
- AI destroyed-unit toggles in the end phase, feeding the next round's plan.
- Each card shows the unit, maneuver, instruction, short reason and weapon
  profile where relevant.

There is no board, no coordinates, no legal-action engine and no dice roller.
The physical table is the board.

## Digital board (secondary)

`/digital` keeps the rules-driven digital match: a deterministic AoS 4th
engine, the fixed server-owned balanced opponent, legal-action validation,
scoring and save/import. It remains available but is not where product work is
focused.

## Principles

- **The table stays physical.** The app calls the play; the player measures,
  moves and rolls.
- **No board state.** Nothing about positions, distances, terrain layout or
  wounds is stored or inferred.
- **Explainable plans.** Every instruction has a short reason grounded in the
  unit's doctrine.
- **Deterministic variation.** The same round and seed replay the same plan,
  and maneuvers rotate so a unit does not repeat the same move every round.
- **No mandatory setup.** Starter rosters and a ready plan mean the app is
  usable before the builder is ever opened.
- **Portable rosters.** JSON import/export and browser-local storage; no
  account.

## Explicit non-goals

- **Points and matched play.** No list-building rules, points caps, battleline
  requirements or tournament validation.
- **A digital board in table mode.** No grid, coordinates, templates, range
  finder or legal-action engine.
- **A dice roller.** The player rolls and resolves at the table.
- **Player-selected aggression or difficulty.** Doctrine comes from the unit
  profile; the player does not pick an AI style.
- **Accounts, cloud sync and matchmaking.** Rosters and the current round live
  in the browser; the stateless planner runs on the local server.
- **A content buffet.** Two starter rosters and a small builder, not a library
  of factions and missions.
- **An LLM or machine-learning opponent.** The planner is deterministic
  heuristic code driven by the seed.
