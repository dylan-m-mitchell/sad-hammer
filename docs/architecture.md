# Architecture

This document describes the major components and data shapes used by Sad Hammer.

Overview

Sad Hammer is intentionally small and modular. The main runtime components are:

- `api_server.py` — lightweight Flask API that constructs `SoloSimulator` instances and manages in-memory sessions. It also serves the frontend static files from `web/`.
- `full_simulator.py` — contains `SoloSimulator` which implements the card-driven AI: tactic pool lifecycle, action deck building, aggression level modifiers, and action resolution ordering. All units participate each turn with aggression affecting tactical execution.
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
  'notes': [...]
}
```

SoloSimulator contract

- `simulate_turn()` — runs a single AI turn: All units receive action cards each turn. Aggression level affects execution modifiers (charge ranges, movement preferences, target priorities) rather than gating participation. Returns structured events including aggression level info and resolved actions. `simulate_turn()` increments the `turn` counter.
- `choose_battle_tactic()` — picks a tactic card from `tactic_pool` and moves it to `tactic_discard`. The Battle Tactic deck is dynamic with cards entering at different turns:
  - Turn 1: 4 cards available (Monstrous Takeover, Ferocious Advance, Aggressive Expansion, Conquer)
  - Turn 2: 1 card added (Broken Ranks)
  - Turn 3: 3 cards added (Bring It Down, Slay the Warlord, Savage Spearhead)
  - This timing matches the original Woehammer blog solo wargaming rules
- Aggression levels (Aggressive/Neutral/Cautious) modify tactical execution. Uses an instance-local RNG seeded via the simulator's constructor for deterministic replay when seeds are provided.

Event shapes

The simulator emits structured event objects in the session log. Common event keys include:

- `event`: event type identifier (e.g., "aggression_level", "action_resolved")
- `unit`: unit name
- `aggression`: unit's aggression level ("Aggressive", "Neutral", or "Cautious")
- `modifiers`: dict containing aggression execution modifiers (charge_range_threshold, run_preference, retreat_threshold, target_priority)
- `action_resolved`: object containing `unit`, `card_title`, `initiative`, `behavior`, `aggression`, `aggression_modifiers`, and additional resolution info
- `text`: optional human-readable text summary

Combat resolution

- In Accurate mode `interactive_simulator.resolve_attack()` is used for an attack action; it performs per-attack to-hit/to-wound/save/damage rolls and updates `Unit.current_wounds` and models remaining.
- Damage expressions support integers and Dice notation (eg. `D3`), and damage is applied per wounds-per-model.

Notes about design choices

- The server intentionally does not model the player's units or the board; the app focuses on the AI opponent and returns events the human resolves.
- Sessions are in-memory for now. A production roadmap includes adding Redis or a lightweight file-backed store to persist sessions across restarts.

Card-only decision model and spatial fallbacks

- The AI is a digitized card system: tactic cards are drawn and action cards are drawn per unit. To faithfully reproduce the card mechanic, the simulator only uses information that would be available to a random card draw: unit attributes (name, keywords, wounds, model counts, aggression) and the seeded RNG.

- Spatial/board-based instructions on printed cards (for example: "closest to objective", "units within 18\" of objective", or "units on one flank") are not actionable by the simulator because cards in the physical system do not have access to placement coordinates. When the `designated_units` text in `reference_card_decks.py` includes spatial instructions, the simulator applies a deterministic attribute-only fallback mapping during deck loading. Examples:

  - "closest to objective" -> fallback to `random` among matching units
  - "within X\" of objective" -> fallback to `all random` (treat as eligible pool)
  - "units on one flank" -> fallback to `random N` where N is specified on the card or a reasonable default

- These fallbacks are deterministic when a session seed is provided (random selections use the session RNG), and are documented in `reference_card_decks.py` as `designated_units_raw` (the original text) alongside the sanitized `designated_units` used by the selector parser.

\*\*\* End of file
