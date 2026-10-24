# GitHub Actions workflows

## `engine-ci.yml`

Focused gate for the new rules engine. Runs on every push and pull request for
Python 3.10 and 3.12:

- Black formatting check for `backend/engine` and `tests/engine`
- Ruff lint
- Engine test suite (`tests/engine`)
- CLI smoke test

This is the fast feedback loop while the engine is being built. It does not
depend on Flask, the frontend or any legacy card simulator.

## `main-ci-cd.yml`

Full repository pipeline on pushes to `main` and pull requests targeting
`main`:

1. **backend-tests** — full pytest suite, including engine tests, on Python
   3.10–3.12, with optional Codecov upload.
2. **backend-quality** — Black and Ruff across `backend/` and `tests/`; MyPy is
   non-blocking while the legacy tree is being retired.
3. **frontend-tests** — `npm ci` and `npm run build`. Browser tests are not yet
   wired up because the existing Playwright specs still describe the retired
   player-roll UI.
4. **docker-build** — builds both images from the repository root (the
   Dockerfiles copy `requirements.txt`, `frontend/` and `nginx/`).
5. **integration-check** — starts the Flask app on port 5000 and runs the opt-in
   live-server test.
6. **deploy** — placeholder on `main` only.
7. **ci-success** — single required status check for branch protection.

## Local equivalents

```bash
# Fast engine loop
pytest tests/engine -q
black --check backend/engine tests/engine
ruff check backend/engine tests/engine

# Full suite
pytest tests/ -q
black --check backend/ tests/
ruff check backend/ tests/

# Live server test
python -c "from backend.api_server import app; app.run(port=5000, debug=False)" &
RUN_LIVE_TESTS=1 LIVE_BASE=http://127.0.0.1:5000 pytest tests/test_integration_live_server.py -q
```

## Conventions

- Create a feature branch before changing the engine.
- Keep commits logical and run the engine gate before pushing.
- The engine's `GameState` schema is versioned. Add a migration when it
  changes; do not rely on CI to catch a stale save format.
- Do not commit rules PDFs, extracted rulebooks or proprietary datasets.
