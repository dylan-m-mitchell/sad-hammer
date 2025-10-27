# Usage Guide

This guide walks through common workflows: running locally, uploading rosters, stepping AI turns, and tips for playtesting.

Running locally

1. Create a virtualenv and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the backend and frontend (two terminals):

```bash
./scripts/start_backend.sh
./scripts/start_frontend.sh
```

Initialize stateless run (upload roster)

- Open the frontend and upload a BattleScribe HTML roster. The uploaded roster becomes the AI-controlled army.
- When initializing, call `POST /api/session_stateless` (the frontend does this for you). The server returns an initial `seed` and a `state` object. The client must persist the `seed`, `turn`, and current `ai_units`.
- Choose the "AI roll handling" option before initializing stateless state:
  - "AI handles rolls": calls to `/api/ai_turn_stateless` will return fully-resolved events.
  - "Player handles AI rolls": `/api/ai_turn_stateless` will pause and return `pending_actions`, which the client can resolve via `/api/resolve_rolls_stateless`.

Stepping AI turns

- Click "Run AI Turn" to call `/api/ai_turn_stateless` with `{ seed, turn, ai_units, roll_mode }`.
- The frontend stores structured events in a log you can inspect and replay. When `roll_mode == 'player'` the server may return `pending_actions` which the client resolves and posts back to `/api/resolve_rolls_stateless`.

Interpreting events

- `aggression_check` events indicate whether a unit ACTed or HELD. They include roll/modifier/target fields when available.
- `action_resolved` events include the action card (title), unit that acted, initiative, and a short behavior description (eg. "attack: target 1 model").

Playtesting tips

- Use deterministic seeds (available in the CLI and `run_simulation` API) to reproduce interesting AI behavior or bugs.
- Acceptance tests live in `tests/` and include examples for aggression, tactic evolution, and deterministic combat.

Developer notes

- To change the AI decks or action behaviors, edit `reference_card_decks.py` and the action resolution code in `full_simulator.py`.
- To adjust how unit aggression is computed, see session creation code in `api_server.py` where the AI unit `aggression_modifier` is derived from parsed profile attributes.

\*\*\* End of file
