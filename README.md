# Sad Hammer — Solo Wargaming AI

This workspace contains a small card-driven AI for solo Age of Sigmar-style play, a BattleScribe HTML parser, and an interactive simulator that can import rosters.

Quick start

1. Create and activate the virtual environment (macOS / zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

If you don't have a `requirements.txt`, install `pytest` and `beautifulsoup4` in your venv.

CLI simulator (developer tool)

Run the interactive simulator with a BattleScribe HTML roster (this is a developer-facing tool that demonstrates parsing and the simplified combat harness):

```bash
python interactive_simulator.py --auto --seed 2 --roster "Current Stormcasts.html"
```

Run tests:

```bash
pytest -q
```

AI-only server (what this app provides)

This project hosts an AI opponent only. Upload a BattleScribe HTML roster and the server will:

- Parse the roster and treat it as the AI-controlled army.
- Drive AI decisions using the card decks (battle tactics and action cards).
- Expose session endpoints so a UI can step the AI turns and display the AI's chosen actions.

Important: the server does NOT model or validate the human player's units or actions. The human player manages their own rules and applies AI events on their side of the table.

Web frontend (recommended UI)

The repository includes a small frontend and API server. The recommended flow:

1. Upload the opponent's roster (BattleScribe HTML) using the frontend → this creates an AI session.
2. Use "Run AI Turn" to have the AI draw tactics/actions and return a structured list of events.
3. The human player resolves those events locally against their own army on the tabletop.

Project layout

- `api_server.py` — Flask API that parses rosters and runs the card-driven AI. Serves the frontend static files.
- `frontend/` — static frontend (`index.html`) that uploads rosters and steps AI turns.
- `battlescribe_parser.py` — lightweight parser for BattleScribe HTML exports.
- `full_simulator.py` — the Solo AI that implements the card logic and returns structured events.

Start the backend API server (after activating your venv):

```bash
./scripts/start_backend.sh
```

Open the frontend in your default browser:

```bash
./scripts/start_frontend.sh
```

Docker (optional)

Run both services with Docker Compose:

```bash
docker compose up --build
```

The frontend will be available at http://localhost:8080 (nginx) and the backend runs on the compose network at port 5000.
