# Engine architecture

## Purpose

Sad Hammer is a physical-table companion. The human plays their army on a real
table and rolls their own dice; the app maintains a digital twin, resolves rules
and dice for the AI, and updates the twin from the human's reported state. The
engine is the source of truth for legality, state transitions and scoring.

It supports multiple editions through a shared core and per-edition modules:

```text
                    +---------------------------+
                    |   client / board UI       |
                    |  digital twin + save/load |
                    +-------------+-------------+
                                  |
                    +-------------v-------------+
                    |   engine.core.session     |
                    | validate -> apply -> log  |
                    +-------------+-------------+
                                  |
              +-------------------+-------------------+
              |                                       |
    +---------v----------+                 +----------v---------+
    | engine.systems.base|                 |     engine.ai      |
    | GameSystem contract|                 | utility + profiles |
    +---------+----------+                 +----------+---------+
              |                                       |
    +---------+----------+                 +----------v---------+
    | aos4 / wh40k11     |                 | legal actions only |
    | rules + data packs |                 | explanations       |
    +--------------------+                 +--------------------+
                                  |
                    +-------------v-------------+
                    |        engine.core        |
                    | geometry, dice, state,    |
                    | events, validation, JSON   |
                    +---------------------------+
```

The legacy Flask endpoints and `SoloSimulator` are not part of this package.
They remain for reference and for the current UI until a new UI consumes the
engine.

## Core contracts

### `GameSystem`

```python
class GameSystem(ABC):
    system_id: str
    name: str
    edition: str

    @property
    def phases(self) -> Sequence[PhaseDefinition]: ...

    def create_game(self, seed: int = 0, **options) -> GameState: ...
    def legal_actions(self, state: GameState) -> list[GameAction]: ...
    def validate_action(self, state: GameState, action: GameAction) -> ValidationResult: ...
    def apply_action(self, state: GameState, action: GameAction) -> ActionResult: ...
    def evaluate_action(self, state, action, side, weights=None) -> float: ...
    def explain_action(self, state, action, side) -> str: ...
    def score(self, state, side) -> int: ...
    def is_terminal(self, state) -> bool: ...
```

The invariants are:

1. **Legal actions only.** `legal_actions` enumerates actions that should pass
   validation. The AI never constructs actions independently.
2. **Validation is explicit.** `validate_action` returns all errors and
   warnings. `GameSession.apply` refuses any action with an error.
3. **No mutation of the input state.** `apply_action` deep-copies the state,
   advances the dice cursor and returns a new state. The session then appends
   stamped events.
4. **Determinism.** Given the same initial state, action list and seed, the
   result must be identical. No wall-clock, global random or environment input
   may affect rules.
5. **System-specific semantics stay in the system.** `GameAction.action_type`,
   payloads and phase ids are opaque to the core.

### `GameAction`

```python
GameAction(
    action_type="move",
    actor_id="unit-id",
    target_id=None,
    destination=Vec2(12, 18),
    payload={"weapon_id": "rifle"},
    tags=("move", "objective"),
)
```

Common fields cover movement, attacks and phase transitions. Everything else
goes in `payload`. Tags are AI hints only; they must not be treated as rules.
`key()` provides a stable key for tie-breaking and logs.

### Events

Events contain `kind`, `message`, `data`, `seq`, `round`, `phase` and `side`.
`GameSession` stamps the metadata and appends them to `state.events`. The event
log is the replayable narrative and the UI's display feed.

## State model

`GameState` is versioned JSON (`schema_version = 1`) and contains:

- `system_id`, `game_id`, `schema_version`
- `board` (width and height in inches)
- `armies` with units, weapons, wounds, models, keywords and points
- `terrain` polygons with cover/line-of-sight/difficult tags
- `objectives` with position, radius and controller
- `deployment_zones` keyed by side
- `round`, `max_rounds`, `active_side`, `phase`, `status`
- `scores`, `command_points`
- `dice` (`seed`, `cursor`)
- `actions` (the ordered action log for replay)
- `events` and free-form `metadata`

Units are represented as one centre point and a base radius for the first
slice. Real systems can add per-model footprints later without changing the
action contract. Terrain uses polygons so rectangles, ruins and irregular
footprints share one geometry implementation.

### Serialization and migrations

- `dumps_state` / `loads_state` use sorted, pretty JSON for readable saves.
- `schema_version` is checked before constructing objects. Unknown versions are
  rejected rather than guessed at.
- Future migrations are explicit functions keyed by source version. Never
  silently drop a field from a saved game.
- Export is client-owned. The API can remain stateless: send the state with an
  action and receive a new state plus events.

### Determinism and replay

Dice are not drawn from Python's global RNG. A die is derived from
`SHA-256(seed:cursor:sides)` and the cursor advances. The state stores only the
seed and cursor. This means:

- save/load resumes the exact dice stream;
- the same seed and action sequence replay identically;
- AI tie-break noise is a separate hash of the seed and action key, so it never
  consumes game dice.

To replay, start from the saved initial state and apply the saved action list.
The event log should match byte-for-byte after canonical serialization. A replay
command will be added once a real system exists.

## Rules modules

### AoS 4th (`engine.systems.aos4`)

Planned responsibilities:

- seven turn phases: Start of Turn, Hero, Movement, Shooting, Charge, Combat,
  End of Turn, with active-player-then-opponent ability windows;
- normal move, run, retreat, shoot, charge, fight and combat-range rules;
- hit/wound/save/damage resolution, mortal damage, wards and ward saves;
- battle-shock and objective control;
- deployment territories, faction terrain and battle-round scoring;
- mission data for one mission and starter-army data packs.

### 40k 11th (`engine.systems.wh40k11`)

Planned responsibilities:

- battle round with two player turns;
- Start of Turn, Command, Movement, Shooting, Charge, Fight, End of Turn;
- Command CP gain, battle-shock, stratagems subset;
- ranged/melee attack sequence, cover, visibility and terrain;
- objective control and mission scoring;
- one current mission and Armageddon starter data packs.

The two modules share geometry, dice, serialization, validation and AI policy,
but not their phase tables, combat tables or mission rules.

## Rules data

Data packs are versioned JSON/YAML, separate from rules code:

```text
data/
  aos4/
    factions/stormcast.json
    factions/skaven.json
    missions/...
  wh40k11/
    factions/space-marines.json
    factions/orks.json
    missions/...
```

A data pack records its source edition, update date and source notes. Never
commit PDFs, copied rulebook text or proprietary datasets. Roster import maps
New Recruit `.ros`/`.rosz` entries onto data-pack ids and reports unmatched
units/wargear instead of guessing.

## AI

The AI is an external policy over `legal_actions`, not part of the rules module:

1. Enumerate legal actions.
2. Score each with system heuristics and the active aggression profile.
3. Add deterministic personality noise.
4. Pick the best action, record alternatives and an explanation.
5. Validate and apply through `GameSession`.

See [AI design](ai-design.md).

## Physical companion flow

### Setup

1. Choose system, mission and board size.
2. Import/build both rosters.
3. Suggest a terrain layout; the human edits it.
4. Suggest AI deployment; the human deploys their army and mirrors both sides.
5. Validate zones, footprints, coherency and objective clearance with warnings.

### AI turn

1. Engine computes a plan from the digital twin.
2. UI steps through the plan: move path, targets, attacks, charge, fight.
3. Engine rolls AI dice and updates the twin.
4. Human confirms each step and moves the physical models.
5. Events update objectives, CP and VP.

### Human turn

1. Human plays and rolls physically.
2. At end of turn, a wizard lets them drag units, remove casualties, mark
   objectives, update CP/VP and add notes.
3. Validation warns about impossible states; the human remains the table
   authority.
4. The next AI turn plans from the updated state.

The companion does not need to observe every human dice roll. It needs an
accurate enough state at the start of each AI turn.

## Future API shape

The engine itself is transport-agnostic. The intended HTTP surface is:

```text
POST /api/games                 create state from system, rosters and options
GET  /api/systems               list systems, phases and supported missions
POST /api/games/actions         validate/apply one action
POST /api/games/ai-turn         choose/apply an AI turn
POST /api/games/validate        structural validation for human edits
GET  /api/health                liveness
```

The client holds the canonical state and sends it with each call. A server-side
cache keyed by game id is an optimization, not the source of truth. Do not add
sessions until state size or latency justifies it.

## Testing strategy

- Unit tests for geometry, dice, serialization and validation.
- Contract tests run against every `GameSystem` implementation.
- Rules tests for each phase, attack sequence and mission score.
- AI tests assert every selected action is legal and deterministic.
- Replay tests apply a recorded action log to a fresh state.
- Property-style tests for invariant preservation once a real system exists.

## Open architectural questions

- Exact per-model footprint representation for coherency and line of sight.
- Whether terrain visibility needs segment/polygon height rules or simpler
  area terrain for v1.
- How much of the human's physical movement path must be mirrored versus only
  the final position.
- State size at full 2,000-point armies; add a cache only if necessary.
- Whether mission decks need a separate scenario/event layer.
