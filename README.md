# Sad Hammer — Solo Wargaming AI

Sad Hammer is a small, card-driven solo AI for Age of Sigmar-style play. It provides
a lightweight BattleScribe HTML roster parser, a Solo AI that uses card decks (tactics
and action cards), and a minimal Flask API + static frontend to run and inspect AI turns.

Note: The simulator is intended to compute and present the enemy army's intentions
and recommended actions (what the AI would try to do). It is primarily an advisory
tool for the player or a client to enact those intentions, not an automatic autoplayer
that takes full control of the enemy army by default.

This repo is intended to be both a playable table tool and a development kit for
experimenting with different rule-fidelity modes (MVP, Accurate, Automated).

Contents

- `api_server.py` — Flask backend exposing stateless simulation endpoints (client holds seed/state).
- `frontend/` — single-file static frontend used for local play/testing.
- `battlescribe_parser.py` — parser for BattleScribe HTML roster exports.
- `full_simulator.py` — Solo AI (tactic pool, aggression checks, action draws).
- `interactive_simulator.py` — combat helpers and simplified model/wounds handling.
- `reference_card_decks.py` — decks of tactics/actions/objectives used by the AI.
- `tests/` — pytest test suite (unit, integration, acceptance).
- `docs/` — project documentation (rule mapping, API, architecture).

Quick start (local development)

1. Create and activate a virtual environment (macOS / zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install runtime and test dependencies:

```bash
pip install -r requirements.txt
```

3. Run tests:

```bash
pytest -q
```

4. Start the backend (development mode):

```bash
./scripts/start_backend.sh
```

5. Start the frontend (Vite dev server):

```bash
./scripts/start_frontend.sh
```

The app will open on http://localhost:5173 and proxy API calls to http://localhost:5000.

Or use Docker Compose to run everything:

```bash
docker compose up --build
```

Frontend framework and styling

- The frontend has been migrated to React + Vite in `frontend/`.
- Baseline styles are intentionally minimal; Tailwind is configured via PostCSS and will be used to (re)introduce accessible, framework-safe styles.
- Build output is served by Nginx in the frontend container and proxied under `/` with API at `/api/`.

High-level usage (stateless)

- Upload a BattleScribe HTML roster (the uploaded roster becomes the AI's army).
- Initialize stateless state with `POST /api/session_stateless`; the server returns an
  initial `seed` and a minimal `state` object. The client is responsible for
  persisting the seed, current `turn`, and the `ai_units` list.
- Use "Run AI Turn" to call `POST /api/ai_turn_stateless` with `{ seed, turn, ai_units, roll_mode }`.
  The server computes deterministic AI behavior for that turn and returns structured
  events (and `pending_actions` when `roll_mode=="player"`).

  Note: the returned structured events are intended to describe the enemy's
  intentions and recommended actions. The client or player may use these to
  enact moves/rolls manually or programmatically; the simulator is not required
  to autonomously take control of the enemy army.

Rule fidelity and roll handling

Sad Hammer supports different fidelity modes; see `docs/rule_mapping.md` for details.
Clients provide a `roll_mode` when initializing stateless state or when calling `/api/ai_turn_stateless`:

- `ai` (default): server executes rolls and returns resolved events.
- `player`: the server will return `pending_actions` for client resolution; the client should resolve and post results to `/api/resolve_rolls_stateless`.

API and developer notes

See `docs/api.md` for a complete API reference. For architecture and data shapes,
read `docs/architecture.md`.

Contributing

- Write tests for new behavior and run the full test suite before opening a PR.
- Keep acceptance tests deterministic by seeding RNGs where appropriate.

License & Credits

This project is a personal/homegrown tool—see repository for authorship and license notes.
