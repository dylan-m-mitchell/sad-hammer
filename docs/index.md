# Sad Hammer Documentation Index

Welcome — this index links the key documentation pages for the Sad Hammer project.

Core docs

- `README.md` — Quick start, overview, and pointers to documentation.
- `docs/api.md` — API reference, examples, event schemas, and the `resolve_rolls` draft contract.
- `docs/architecture.md` — Architecture overview: SoloSimulator, session model, event shapes.
- `docs/usage.md` — Usage guide, playtesting tips, and developer notes.
- `docs/rule_mapping.md` — Mapping of app behavior to GH2021 rules and fidelity levels.

Recent changes

- Added `roll_mode` per-session setting to let players decide whether the AI or the player handles AI dice rolls.
- Implemented `POST /api/session/<id>/resolve_rolls` server endpoint to accept player-provided roll results and complete paused AI turns.
- Added frontend UI to display pending roll requests and submit roll results.
- Added server-side validation for die roll values and tests covering accept/reject cases.

How to contribute

- Edit docs in `docs/` and open a PR on the feature branch `feature/rule-mapping-accurate`.
- Run `pytest -q` to ensure tests pass before committing.

*** End of file
