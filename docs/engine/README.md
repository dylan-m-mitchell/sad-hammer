# Sad Hammer engine

The engine is a deterministic, rules-driven opponent for a playable digital
tabletop game. The player commands their army in the React client; the engine
owns legality, state transitions, rules resolution, dice, scoring and the AI
opponent. Edition-specific rules live behind the shared `GameSystem` contract:

```text
backend/engine/
  core/       geometry, dice, state, events, validation, serialization, session
  systems/    GameSystem interface + per-edition rules modules + match orchestration
  ai/         legal-action utility AI and internal opponent profiles
  cli.py      local AI-vs-AI verification harness
```

The first real implementation is the AoS 4th core-rules vertical slice. A
small two-phase demo system remains in place to prove the shared contracts in
isolation. The 40k module is the next rules implementation.

## Status

| Area | State |
| --- | --- |
| Free current-edition rules references | Indexed in [rules-references.md](rules-references.md) |
| Engine architecture and state schema | Documented in [architecture.md](architecture.md) |
| Deterministic dice, geometry, state, events, validation | Implemented |
| `GameSystem` interface and demo system | Implemented |
| Explainable legal-action AI | Implemented |
| AoS 4th core-rules vertical slice | Implemented |
| Player-vs-AI web match and play API | Implemented for AoS 4th |
| CLI harness and tests | Implemented |
| 40k 11th rules module | After the AoS vertical slice |
| Editable terrain and expanded deployment UI | Planned |

## Play

The product flow is browser-first:

```bash
docker compose up --build
# open http://localhost:8080
```

The app opens on a one-click default game against the fixed, server-owned
balanced opponent, with optional mission/force/seed customization. It supports
deployment, orders, automatic AI turns, human combat picks in alternating
combat, battle scoring, and versioned save/export/import. The old card simulator
is still reachable at `/legacy`.

The CLI is the engine verification harness. It runs both sides through the
shared utility AI to check rules, legality and replay behaviour; it is not the
primary way to play:

```bash
# A complete AI-vs-AI Age of Sigmar 4th verification game.
python -m backend.engine.cli aos4 --seed 11 --rounds 5 --auto-deploy

# A headless benchmark batch for AI tuning and regression.
python -m backend.engine.cli aos4-bench --games 20

# The smaller contract-proving demo.
python -m backend.engine.cli demo --seed 7 --rounds 2

# Save and inspect the final state.
python -m backend.engine.cli aos4 --seed 7 --rounds 1 --auto-deploy \
  --json --save /tmp/aos4-state.json
python -m backend.engine.cli inspect /tmp/aos4-state.json
```

Run the focused test suite:

```bash
pytest tests/engine -q
pytest tests/test_api_aos4.py -q
```

## Reading order

1. [Roadmap](roadmap.md) — phases, exit criteria and current work.
2. [Architecture](architecture.md) — interfaces, state, determinism and APIs.
3. [AoS 4th slice](aos4-slice.md) — implemented rules, data, UI and simplifications.
4. [Rules references](rules-references.md) — official free rules links and scope.
5. [AI design](ai-design.md) — how the opponent chooses and explains actions.

## Design constraints

- The player issues orders through a digital board. The engine validates and
  resolves those orders, and the same action contract drives the AI.
- The human and the AI may only select actions owned by their own side, including
  during alternating combat.
- The board is a full digital twin: terrain and both armies are tracked in state.
  Editable terrain controls are planned; deployment already uses legal actions.
- Rules live in edition modules. A universal action-card deck is not the turn
  engine.
- Aggression is an AI policy input, not a game rule.
- Saved games are versioned JSON and must be replayable from a seed and action
  log.
- Rules PDFs and large copyrighted text are never committed. Keep links,
  summaries, structured data and user-supplied rosters.
