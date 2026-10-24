# AI design

The AI must feel like an opponent, not a random action generator and not a
single universal card deck. It chooses only from actions the rules module says
are legal and explains the important ones.

The player-facing opponent is fixed. For new games, the server always uses the
internal `balanced` profile, and the player is never asked to choose an AI
style, aggression level or difficulty. The other profiles described below are
internal testing and tuning tools.

## Decision pipeline

```text
state
  -> system.legal_actions(state)
  -> system.evaluate_action(action, balanced profile weights)
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

## Opponent profile and internal profiles

The product uses one server-owned profile: `balanced`. New games always use it
regardless of any `ai_profile` supplied to the API. `GET /api/aos4/options` does
not expose profiles, and importing a game restores the profile recorded in the
save rather than accepting a client override.

An `AggressionProfile` is a set of weights, not a rule:

| Weight | Meaning | Aggressive | Cautious |
| --- | --- | --- | --- |
| `objective_focus` | VP and board control | low/medium | high |
| `damage_focus` | kill potential and threat | high | low/medium |
| `risk_tolerance` | accepting retaliation | high | low |
| `cover_focus` | defensive positioning | low | high |
| `mobility` | tempo and board reach | high | lower |
| `noise` | variation between games | higher | lower |

The repository keeps three internal profiles: `aggressive`, `balanced` and
`cautious`. They are available to the CLI, tests and benchmarks for comparison
and regression coverage. They are not player-facing options, and a player-facing
profile picker must not be added.

Unit-level aggression could later override the global profile for individual
characters or berserk units as an internal modelling detail, not as a player
setting.

## Fairness and difficulty

Difficulty is not player-selected. There is no casual/standard/veteran menu and
no aggression slider. The single balanced opponent is tuned to be fair and
deliberately beatable: it makes legal, explainable choices and can be beaten by
good play, but it is not optimized for tournament-level tactics.

Difficulty changes, if any, belong to tuning the same heuristics. They must not
change legality, grant hidden bonuses, or give the AI information the player
does not have.

There is no LLM, machine-learning or reinforcement-learning component, and none
is planned. The AI also has no dependency on human gameplay data.

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
same seed and profile replay exactly; different seeds produce different but
legal choices. Tests must assert both.

## Evaluation and regression

- Run the headless benchmark before and after changing AI weights or heuristics:

  ```bash
  python -m backend.engine.cli aos4-bench --games 20
  ```

  It plays a batch of balanced AI-vs-AI games without the web client. Use it to
  compare outcomes, VP spread, game length and legality, and to judge whether a
  change makes the product opponent better or worse.
- Use AI-vs-AI batches as an engine regression harness, not as the product
  experience.
- Assert zero illegal actions and no action loops.
- Measure VP spread, game length, unit usage and objective participation.
- Compare internal profiles in harness runs to ensure they produce meaningfully
  different behavior without being irrational.
- Keep recorded games as regression fixtures for rules and AI changes.

## Explicit non-goals

- LLM or machine-learning opponents, now or later.
- A dependency on human gameplay data.
- Player-selected AI profiles, aggression levels or difficulty.
- A universal card/tactic deck driving either edition.
- Perfect tactical play or tournament-level list optimization.
- Pretending to know hidden information the AI would not have.
