# Sad Hammer engine

The engine is a deterministic, rules-driven tabletop opponent for **Age of
Sigmar 4th edition** and **Warhammer 40,000 11th edition**. It is a separate
package from the legacy card-driven solo simulator:

```text
backend/engine/
  core/       geometry, dice, state, events, validation, serialization, session
  systems/    GameSystem interface + per-edition rules modules
  ai/         legal-action utility AI and aggression profiles
  cli.py      local walking-skeleton harness
```

The first implementation is a small two-phase demo system. It exists to prove
the shared contracts, not to represent either commercial game. The real rules
modules are described in the roadmap.

## Status

| Area | State |
| --- | --- |
| Free current-edition rules references | Indexed in [rules-references.md](rules-references.md) |
| Engine architecture and state schema | Documented in [architecture.md](architecture.md) |
| Deterministic dice, geometry, state, events, validation | Implemented |
| `GameSystem` interface and demo system | Implemented |
| Explainable legal-action AI | Implemented |
| CLI walking skeleton and tests | Implemented |
| AoS 4th rules module | Next phase |
| 40k 11th rules module | After the AoS vertical slice |
| Digital-twin board UI | After the AoS engine slice |

## Try it

```bash
python -m backend.engine.cli demo --seed 7 --rounds 2
python -m backend.engine.cli demo --seed 7 --rounds 1 --json --save /tmp/demo-state.json
python -m backend.engine.cli inspect /tmp/demo-state.json
```

Run the focused test suite:

```bash
pytest tests/engine -q
```

## Reading order

1. [Roadmap](roadmap.md) — phases, exit criteria and current work.
2. [Architecture](architecture.md) — interfaces, state, determinism and APIs.
3. [Rules references](rules-references.md) — official free rules links and scope.
4. [AI design](ai-design.md) — how the opponent chooses and explains actions.

## Design constraints

- The human plays and rolls physically. The app rolls only for the AI and
  updates the digital twin from the human's reported state.
- The board is a full digital twin: terrain and both armies are editable.
- Rules live in edition modules. A universal action-card deck is not the turn
  engine.
- Aggression is an AI policy input, not a game rule.
- Saved games are versioned JSON and must be replayable from a seed and action
  log.
- Rules PDFs and large copyrighted text are never committed. Keep links,
  summaries, structured data and user-supplied rosters.
