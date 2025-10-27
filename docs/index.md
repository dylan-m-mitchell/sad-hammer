# Sad Hammer Documentation Index

Welcome — this index links the key documentation pages for the Sad Hammer project.

Core docs

- `README.md` — Quick start, overview, and pointers to documentation.
- `docs/api.md` — API reference, examples, event schemas, and the `resolve_rolls` draft contract.
- `docs/architecture.md` — Architecture overview: SoloSimulator, session model, event shapes.
- `docs/usage.md` — Usage guide, playtesting tips, and developer notes.
- `docs/rule_mapping.md` — Mapping of app behavior to GH2021 rules and fidelity levels.

Recent changes

- Added `roll_mode` concept to allow clients to select who handles AI dice rolls. In the stateless flow clients provide the `roll_mode` when calling `/api/session_stateless` and `POST /api/ai_turn_stateless`.
- Implemented stateless roll resolution endpoints (`/api/ai_turn_stateless`, `/api/resolve_rolls_stateless`) to support both server-resolved and client-resolved flows without persisting server-side session state.
- Added frontend UI to display pending roll requests and submit roll results (client-side handling recommended when `roll_mode == 'player'`).
- Added server-side validation for die roll values and tests covering accept/reject cases.

How to contribute

- Edit docs in `docs/` and open a PR on the feature branch `feature/rule-mapping-accurate`.
- Run `pytest -q` to ensure tests pass before committing.

\*\*\* End of file
