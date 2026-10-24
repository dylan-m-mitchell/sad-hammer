# AI design

The AI must feel like an opponent, not a random action generator and not a
single universal card deck. It chooses only from actions the rules module says
are legal and explains the important ones.

## Decision pipeline

```text
state
  -> system.legal_actions(state)
  -> system.evaluate_action(action, profile weights)
  -> deterministic personality noise
  -> ranked decisions + explanation
  -> system.validate_action
  -> GameSession.apply
```

The policy never invents targets, destinations or phases. If a rule is missing,
the action is missing; if a move is illegal, it is not in the list.

## Scoring layers

The system provides the base value of an action. A real edition module should
combine:

- **Damage:** expected hits, wounds, failed saves and damage, including
  multi-damage spill and overkill.
- **Objective value:** VP swing, control, denial, and whether the unit can
  survive to score.
- **Tempo:** does this action consume a resource or phase that is needed
  elsewhere?
- **Threat:** what the target can do next turn if left alive.
- **Risk:** retaliation, charge range, line of sight, terrain and CP cost.
- **Board control:** screening, zoning, lane denial and reserve pressure.
- **Durability:** wounds, models, wards, saves and defensive stratagems.

The demo implements a small subset so the interface is exercised.

## Aggression and personality

An `AggressionProfile` is a set of weights, not a rule:

| Weight | Meaning | Aggressive | Cautious |
| --- | --- | --- | --- |
| `objective_focus` | VP and board control | low/medium | high |
| `damage_focus` | kill potential and threat | high | low/medium |
| `risk_tolerance` | accepting retaliation | high | low |
| `cover_focus` | defensive positioning | low | high |
| `mobility` | tempo and board reach | high | lower |
| `noise` | variation between games | higher | lower |

Three initial profiles are provided: `aggressive`, `balanced`, `cautious`.
Difficulty should be a separate preset that changes lookahead and mistake rate,
not a rules handicap. Unit-level aggression can later override the global
profile for individual characters or berserk units.

## Explainability

Every `Decision` carries:

- the selected action;
- its score and base score;
- a human-readable reason from the system;
- the best alternatives.

The UI should show a short “why” line, not a wall of weights. For example:

- “Shoot the objective holder: it can score next turn and is the largest
  immediate threat.”
- “Move into cover: the unit is below half strength and can still contest the
  centre.”
- “Hold the objective: charging would leave the unit exposed to the enemy’s
  counter-attack.”

Logs and explanations are part of the replay. They are not generated from a
different model after the fact.

## Determinism and variety

The game seed drives dice and event order. AI tie-breaking uses a separate
deterministic hash of the seed and action key, so it does not consume dice. The
same seed and profiles replay exactly; different seeds produce different but
legal choices. Tests must assert both.

## Difficulty levels

Planned presets:

- **Casual:** more noise, shorter lookahead, occasional conservative fallback.
- **Standard:** full v1 heuristics with moderate noise.
- **Veteran:** stronger threat/objective evaluation, lower noise, better
  resource sequencing.

Difficulty must not change legality or secretly grant bonuses. It changes how
well the AI evaluates the same information a human has.

## Evaluation and regression

- Use AI-vs-AI batches as an engine regression harness, not as the product
  experience.
- Assert zero illegal actions and no action loops.
- Measure VP spread, game length, unit usage and objective participation.
- Compare aggression profiles to ensure they produce meaningfully different
  behavior without being irrational.
- Keep recorded games as regression fixtures for rules and AI changes.

## Explicit non-goals for v1

- Machine learning or reinforcement learning.
- A universal card/tactic deck driving either edition.
- Perfect tactical play or tournament-level list optimization.
- Pretending to know hidden information the AI would not have.
