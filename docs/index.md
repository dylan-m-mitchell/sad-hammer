# Sad Hammer Documentation Index

Welcome — this index links the key documentation pages for the Sad Hammer project.

Core docs

- `README.md` — Quick start, overview, and pointers to documentation.
- `docs/api.md` — API reference, examples, event schemas, and the `resolve_rolls` draft contract.
- `docs/architecture.md` — Architecture overview: SoloSimulator, session model, event shapes.
- `docs/usage.md` — Usage guide, playtesting tips, and developer notes.
- `docs/rule_mapping.md` — Mapping of app behavior to GH2021 rules and fidelity levels.

Recent changes

- Removed player roll mode in favor of simplified AI-only mode for better user experience.
- Implemented stateless AI turn endpoint (`/api/ai_turn_stateless`) where the server automatically resolves all dice rolls and actions.
- All units now act every turn - aggression levels modify how units execute their actions rather than whether they act.

How to contribute

- Edit docs in `docs/` and open a PR on the feature branch `feature/rule-mapping-accurate`.
- Run `pytest -q` to ensure tests pass before committing.

\*\*\* End of file
