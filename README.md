# Sad Hammer — Solo Wargaming AI

Sad Hammer is a small, card-driven solo AI for Age of Sigmar-style play. It provides
a lightweight BattleScribe HTML roster parser, a Solo AI that uses card decks (tactics
and action cards), and a minimal Flask API + static frontend to run and inspect AI turns.

This repo is intended to be both a playable table tool and a development kit for
experimenting with different rule-fidelity modes (MVP, Accurate, Automated).

Contents

- `api_server.py` — Flask backend and session manager.
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

High-level usage

- Upload a BattleScribe HTML roster (the uploaded roster becomes the AI's army).
- Create a session; the server returns a session ID and persists session state in-memory.
- Use "Run AI Turn" to have the server draw tactics/actions and return a human-readable
  text summary plus structured JSON events. The human player resolves those events
  at the table against their physical units.

Rule fidelity and roll handling

Sad Hammer supports different fidelity modes; see `docs/rule_mapping.md` for details.
Sessions also support a `roll_mode` (per-session) that controls who provides the AI's
dice rolls:

- `ai` (default): server executes rolls and returns resolved events.
- `player`: player resolves AI rolls locally; the server persists the flag and clients
  can opt to use a server-mediated roll-request flow (planned) or resolve locally.

API and developer notes

See `docs/api.md` for a complete API reference. For architecture and data shapes,
read `docs/architecture.md`.

Contributing

- Write tests for new behavior and run the full test suite before opening a PR.
- Keep acceptance tests deterministic by seeding RNGs where appropriate.

License & Credits

This project is a personal/homegrown tool—see repository for authorship and license notes.
