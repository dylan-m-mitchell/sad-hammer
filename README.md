# Sad Hammer

Sad Hammer is a physical-table companion and AI opponent for miniature
wargames. The human plays their army on a real table and rolls their own dice;
the app maintains a digital twin of the board, resolves rules and dice for the
AI, and explains what the AI is doing.

The v1 target is **Warhammer Age of Sigmar 4th edition** and **Warhammer 40,000
11th edition**, starting with one mission and the starter-box forces for each
system.

## New engine

The next generation of Sad Hammer lives in `backend/engine/`:

- deterministic dice and replayable state;
- geometry for boards, deployment zones, terrain and objectives;
- versioned JSON saves with validation;
- a `GameSystem` interface for edition-specific rules;
- a rules-based, explainable utility AI with aggression profiles;
- a CLI walking skeleton and a focused test suite.

Read:

- [Engine overview](docs/engine/README.md)
- [Roadmap](docs/engine/roadmap.md)
- [Architecture](docs/engine/architecture.md)
- [Rules references](docs/engine/rules-references.md)
- [AI design](docs/engine/ai-design.md)

Try the walking skeleton:

```bash
python -m backend.engine.cli demo --seed 7 --rounds 2
python -m backend.engine.cli demo --seed 7 --rounds 1 --save /tmp/demo-state.json
python -m backend.engine.cli inspect /tmp/demo-state.json
pytest tests/engine -q
```

## Repository status

`backend/engine/` is the new rules engine. The existing Flask API, React
frontend and card-driven simulator are **legacy reference code** for the
retired AoS 3/GHB2021 solo-card flow. They remain runnable while the new AoS
slice is built, but they are not the architecture for the new opponent.

| Area | Status |
| --- | --- |
| Shared engine core and demo system | Implemented |
| AoS 4th rules module | Next |
| 40k 11th rules module | After the AoS slice |
| Digital-twin board and deployment UI | Planned |
| New Recruit `.ros`/`.rosz` import and curated builder | Planned |

## Legacy application

The old app still has its original local setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
./scripts/start_backend.sh   # http://localhost:5000
./scripts/start_frontend.sh  # http://localhost:5173
```

Or with Docker:

```bash
docker compose up --build
# http://localhost:8080
```

The legacy docs in `docs/` describe that flow. They should be treated as
historical until the new UI replaces them.

## CI

- `.github/workflows/engine-ci.yml` — fast engine formatting, lint, tests and
  CLI smoke test.
- `.github/workflows/main-ci-cd.yml` — full backend/frontend/docker/integration
  checks on pull requests to `main`.

See [`.github/workflows/README.md`](.github/workflows/README.md) for details.

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
