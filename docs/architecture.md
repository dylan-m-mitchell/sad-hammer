# Architecture

This document describes the major components and data shapes used by Sad Hammer.

Overview

Sad Hammer is intentionally small and modular. The main runtime components are:

- `api_server.py` — lightweight Flask API that constructs `SoloSimulator` instances and manages in-memory sessions. It also serves the frontend static files from `web/`.
- `full_simulator.py` — contains `SoloSimulator` which implements the card-driven AI: tactic pool lifecycle, action deck building, aggression checks, and action resolution ordering.
- `interactive_simulator.py` — contains `Unit` model for wounds and a combat resolver used in Accurate mode for roll-by-roll attack resolution.
- `battlescribe_parser.py` — extracts unit profiles and weapon data from BattleScribe HTML exports.
- `reference_card_decks.py` — data file defining tactic/action/objective cards used by the AI.

Session model

Sessions are stored in-memory in `api_server.py` as a dict keyed by UUID:

```
SESSIONS[session_id] = {
  'sim': SoloSimulator(...),
  'ai_units': [...AIUnit instances...],
  'ai_profiles': [...parsed profile objects...],
  'log': [...structured events...],
  'notes': [...],
  'roll_mode': 'ai'|'player'
}
```

SoloSimulator contract

- `simulate_turn()` — runs a single AI turn: evaluates aggression checks for each unit, chooses a battle tactic, builds the action deck for drawn actions, resolves each action in initiative order, appends structured events and returns the events for that turn. `simulate_turn()` increments the `turn` counter.
- `choose_battle_tactic()` — picks a tactic card from `tactic_pool` and moves it to `tactic_discard`. The tactics "Broken Ranks" and the remaining tactics are added based on the simulator's `turn` value (turn 2 and 3 respectively).
- Aggression checks use an instance-local RNG seeded via the simulator's constructor for deterministic replay when seeds are provided.

Event shapes

The simulator emits structured event objects in the session log. Common event keys include:

- `aggression_check`: boolean (true when unit acted)
- `unit`: unit name
- `roll`, `modifier`, `total`, `target`: aggression check debug fields
- `action_resolved`: object containing `unit`, `card_title`, `initiative`, `behavior`, and additional resolution info
- `text`: optional human-readable text summary

Combat resolution

- In Accurate mode `interactive_simulator.resolve_attack()` is used for an attack action; it performs per-attack to-hit/to-wound/save/damage rolls and updates `Unit.current_wounds` and models remaining.
- Damage expressions support integers and Dice notation (eg. `D3`), and damage is applied per wounds-per-model.

Notes about design choices

- The server intentionally does not model the player's units or the board; the app focuses on the AI opponent and returns events the human resolves.
- `roll_mode` is persisted per session so clients can decide whether they want to resolve AI rolls locally.
- Sessions are in-memory for now. A production roadmap includes adding Redis or a lightweight file-backed store to persist sessions across restarts.

\*\*\* End of file
