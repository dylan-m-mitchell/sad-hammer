# Sad Hammer Documentation Index

The project is moving from a card-driven AoS 3 prototype to a rules-driven,
multi-system tabletop opponent. Start with the new engine docs.

New engine

- `docs/engine/README.md` — overview, status and local commands.
- `docs/engine/roadmap.md` — phased plan, exit criteria and risks.
- `docs/engine/architecture.md` — engine interfaces, state schema and APIs.
- `docs/engine/rules-references.md` — official free rules links and scope.
- `docs/engine/ai-design.md` — utility AI, aggression and explainability.

Legacy reference docs

These describe the existing Flask/React card prototype. They remain useful for
understanding the code that has not yet been replaced, but they are not the
target architecture.

- `docs/api.md` — legacy API reference.
- `docs/architecture.md` — legacy `SoloSimulator` and session model.
- `docs/usage.md` — legacy usage guide.
- `docs/rule_mapping.md` — legacy GHB2021 mapping.
- `docs/architecture-decisions.md` — historical file-layout decisions.

Contributing

- Branch before changing the engine.
- Run `pytest tests/engine -q` for the fast engine loop.
- Run `pytest tests/ -q`, Black and Ruff before opening a pull request.
- Do not commit rules PDFs, extracted rulebooks or proprietary datasets.
