# Sad Hammer

Sad Hammer is a table companion for Warhammer Age of Sigmar 4th. You set up
your miniatures and roll the dice; the app directs the AI army from unit
profiles and doctrine. It has no board, no coordinates, no legal-action engine
and no dice roller — every instruction is relative table language such as
"closest enemy" or "within 12 inches".

The rules-driven digital board game is preserved at `/digital`, and the original
card prototype at `/legacy`. The table companion at `/` is the primary
experience.

## Get started

```bash
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080).

The app opens with two starter rosters already loaded — your Stormcast Eternals
and the AI's Skaven — plus a setup checklist and the AI plan for round one. No
army, mission, points or difficulty choice is required.

| Route | Experience |
| --- | --- |
| `/` | Table Companion — the primary experience |
| `/digital` | The board-tracking digital game, preserved on the back burner |
| `/legacy` | The original card-driven prototype, unchanged |

## Table companion

- **Setup checklist.** Place objectives and terrain, deploy your army, then
  deploy the AI army with its doctrine guide: Press forward, Support in cover,
  Hold near objectives.
- **AI roster and round counter.** Mark destroyed AI units with a simple toggle
  and advance the battle round.
- **Phase cards.** Hero, Movement, Shooting, Charge, Combat and End. Each entry
  names the unit, maneuver, instruction and short reason, with the relevant
  weapon profile attached.
- **Type-based doctrine.** Press units close and charge; Support units shoot
  from range and never default to charging; Hold units support the line and
  sit on objectives.
- **Seeded variation.** The same round and seed replay the same plan, and each
  unit's maneuver rotates from round to round.
- **Custom rosters.** Build by hand or import/export JSON. Your roster and the
  AI's can be swapped. Both are saved in browser localStorage and can be edited
  freely; there are no points or matched-play rules.

The planner is a stateless endpoint: it receives both rosters, the round, a
seed and the destroyed AI unit IDs, and returns deterministic phase cards. It
never receives or infers positions, distances, terrain or wounds.

See [docs/table-mode.md](docs/table-mode.md) for the roster format, doctrine
table and HTTP API.

## Digital board game

`/digital` keeps the earlier rules-driven game: Stormcast Eternals vs Skaven on
Contested Ground, with both armies deployed for five rounds against the fixed,
server-owned balanced AI. It supports movement, shooting, charge, combat and
command orders on a responsive board, alternating combat, objectives, command
points, scoring, explanations and versioned save/export/import.

The digital game is intentionally on the back burner. Its engine and API are
unchanged by table mode.

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

The focused table companion checks:

```bash
pytest tests/test_table_rosters.py tests/test_table_planner.py tests/test_table_api.py -q
```

Formatting, lint and the engine test loop:

```bash
black --check backend/engine tests/engine
ruff check backend/engine tests/engine
pytest tests/engine -q
```

## Architecture

The table companion is a small stateless package:

```
backend/
  table/
    rosters.py   roster parsing, canonical IDs and starter rosters
    planner.py   doctrine classification and seeded maneuver cards
  table_api.py   /api/table/rosters, /rosters/validate and /plan
frontend/src/table/
  TableApp.jsx      setup, roster, round and plan flow
  RosterBuilder.jsx manual builder and JSON import/export
  SetupChecklist.jsx
  AiRosterPanel.jsx
  PhaseCard.jsx / TurnView.jsx
```

It reads starter profiles from the curated faction packs in `data/aos4/` and
shares no game state with the digital engine.

The digital board game in `backend/engine/` remains a deterministic engine with
geometry, dice, state, a `GameSystem` interface, an AoS 4th core-rules slice, a
rules-based utility AI with explanations, and a Flask play API.

Read:

- [Product](docs/product.md)
- [Table companion guide](docs/table-mode.md)
- [Engine overview](docs/engine/README.md)
- [Roadmap](docs/engine/roadmap.md)
- [Architecture](docs/engine/architecture.md)
- [AoS 4th vertical slice](docs/engine/aos4-slice.md)
- [Rules references](docs/engine/rules-references.md)
- [AI design](docs/engine/ai-design.md)
- [HTTP API](docs/api.md) (legacy API reference)

### Engine verification harness

The CLI can run both sides of the digital game through the AI for rules and
regression testing. This AI-vs-AI mode is a test harness, not the product
experience:

```bash
# A five-round AI-vs-AI verification game.
python -m backend.engine.cli aos4 --seed 11 --rounds 5 --auto-deploy

# A headless balanced AI-vs-AI benchmark for AI tuning and regression.
python -m backend.engine.cli aos4-bench --games 20

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
| Table companion planner, setup checklist and phase cards | Implemented |
| Starter Stormcast and Skaven rosters | Implemented |
| Custom roster builder, JSON import/export and localStorage | Implemented |
| Seeded maneuver variation and destroyed-unit filtering | Implemented |
| Digital AoS 4th board game at `/digital` | Implemented, back burner |
| Shared engine core and demo system | Implemented |
| AoS 4th core-rules slice | Implemented |
| Editable terrain and full deployment editor (digital) | Planned |
| 40k 11th rules module | After the AoS slice |
| New Recruit `.ros`/`.rosz` import and curated builder | Planned |

## Contributing

- Branch before changing the engine.
- Keep table mode stateless: no positions, distances, terrain state or wound
  tracking may enter the table planner.
- Keep rules code out of the AI layer and edition data out of the core.
- Add tests for every rules action, state transition and AI legality claim.
- Never commit rules PDFs, extracted rulebooks or proprietary datasets. Keep
  official links, summaries, structured data and user-supplied rosters.

## License and credits

This is a personal/homegrown project. See the repository for authorship and
license notes. Warhammer and Age of Sigmar are trademarks of Games Workshop;
this project is unofficial and is not endorsed by Games Workshop.
