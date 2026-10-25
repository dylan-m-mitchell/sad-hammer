# Sad Hammer Documentation Index

Start with the product definition. Sad Hammer is now a table companion: it
directs the AI army from unit profiles and doctrine while the player measures,
moves and rolls on a real tabletop. The digital board game is preserved at
`/digital` and the card prototype at `/legacy`.

Product

- `docs/product.md` — purpose, routes, core loop, planner and non-goals.
- `docs/table-mode.md` — table flow, roster format, doctrine table and
  `/api/table` contract.

Digital engine (secondary)

- `docs/engine/README.md` — overview, status and local commands.
- `docs/engine/roadmap.md` — phased plan, exit criteria and risks.
- `docs/engine/architecture.md` — engine interfaces, state schema and APIs.
- `docs/engine/rules-references.md` — official free rules links and scope.
- `docs/engine/ai-design.md` — fixed opponent, utility AI and explainability.
- `docs/engine/aos4-slice.md` — implemented rules, data, UI and simplifications.

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
- Keep table mode stateless; never add board state to the table planner.
- Run `pytest tests/test_table_*.py -q` for the table loop.
- Run `pytest tests/ -q`, Black and Ruff before opening a pull request.
- Do not commit rules PDFs, extracted rulebooks or proprietary datasets.
