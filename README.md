# Sad Hammer

Sad Hammer is a playable, rules-driven digital tabletop opponent for miniature
wargames. Open it on a phone or in a desktop browser, choose a force and fight a
quick game against an explainable AI opponent.

The first playable game is **Warhammer Age of Sigmar 4th edition**, using the
Skaventide starter forces and one original mission. **Warhammer 40,000 11th
edition** follows on the same shared engine.

## Play Age of Sigmar 4th

```bash
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080), pick an AI style and start
the battle. The app supports the complete game loop:

- choose a mission, starter force and AI aggression profile;
- deploy your army and issue movement, shooting, charge, combat and command
  orders on a responsive board;
- see the AI's decisions and the reasons behind them;
- resolve alternating combat without either side controlling the other's units;
- track command points, objective control, battle round and victory points;
- export a versioned save, import it later, or resume the game from the same
  browser.

The old card-driven simulator remains available at `/legacy` for reference.

## Development

Prerequisites: Python 3.10+ and Node.js 18+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1: Flask API on http://localhost:5000
./scripts/start_backend.sh

# Terminal 2: Vite app on http://localhost:8080
./scripts/start_frontend.sh
```

Run the tests:

```bash
pytest tests/ -q
cd frontend && npm run build
```

The engine's focused formatting, lint and test command:

```bash
black --check backend/engine tests/engine
ruff check backend/engine tests/engine
pytest tests/engine -q
```

## Architecture

The player-facing game is built on a deterministic engine in
`backend/engine/`:

- deterministic dice and replayable, versioned JSON state;
- geometry for boards, deployment zones, terrain and objectives;
- a `GameSystem` interface for edition-specific rules;
- an AoS 4th core-rules slice with two starter forces and one mission;
- a rules-based utility AI with aggression profiles and explanations;
- a Flask play API and a responsive React client.

Read:

- [Engine overview](docs/engine/README.md)
- [Roadmap](docs/engine/roadmap.md)
- [Architecture](docs/engine/architecture.md)
- [AoS 4th vertical slice](docs/engine/aos4-slice.md)
- [Rules references](docs/engine/rules-references.md)
- [AI design](docs/engine/ai-design.md)
- [HTTP API](docs/api.md)

### Engine verification harness

The CLI can run both sides through the AI for rules and regression testing.
This AI-vs-AI mode is a test harness, not the product experience:

```bash
# A five-round AI-vs-AI verification game.
python -m backend.engine.cli aos4 --seed 11 --rounds 5 --auto-deploy

# The small demo system used to prove the shared contracts.
python -m backend.engine.cli demo --seed 7 --rounds 2

# Save and inspect a game state.
python -m backend.engine.cli aos4 --seed 7 --rounds 1 --auto-deploy \
  --save /tmp/aos4-state.json
python -m backend.engine.cli inspect /tmp/aos4-state.json
```

## Status

| Area | Status |
| --- | --- |
| Shared engine core and demo system | Implemented |
| AoS 4th core-rules slice | Implemented |
| Player-vs-AI web game | Implemented for the AoS slice |
| Alternating combat with side ownership | Implemented |
| Save/export/import and resume | Implemented |
| Editable terrain and full deployment editor | Planned |
| 40k 11th rules module | After the AoS slice |
| New Recruit `.ros`/`.rosz` import and curated builder | Planned |

## Contributing

- Branch before changing the engine.
- Keep rules code out of the AI layer and edition data out of the core.
- Add tests for every rules action, state transition and AI legality claim.
- Never commit rules PDFs, extracted rulebooks or proprietary datasets. Keep
  official links, summaries, structured data and user-supplied rosters.

## License and credits

This is a personal/homegrown project. See the repository for authorship and
license notes. Warhammer and Age of Sigmar are trademarks of Games Workshop;
this project is unofficial and is not endorsed by Games Workshop.
