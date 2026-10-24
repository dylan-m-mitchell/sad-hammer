# Engine architecture

## Purpose

Sad Hammer is a playable digital tabletop game. The human commands their army in
a mobile or desktop browser, while the app maintains the board state, resolves
rules and dice, and supplies the AI opponent. The engine is the source of truth
for legality, state transitions and scoring. A physical-table mirror mode may be
added later, but it is not required for the product flow.

It supports multiple editions through a shared core and per-edition modules:

```text
                    +---------------------------+
                    |   client / board UI       |
                    |  board state + save/load |
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
`GameSession` fills missing metadata from the state before the action and
appends the event to `state.events`. Systems can stamp a transition event with
the destination phase, round or side when those differ from the previous state.
The event log is the replayable narrative and the UI's display feed.

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

Implemented in the first vertical slice:

- seven turn phases: Start of Turn, Hero, Movement, Shooting, Charge, Combat,
  End of Turn;
- normal move, run, retreat, shoot, charge and fight;
- hit/wound/save/damage resolution, critical-mortal damage, ward rolls and
  destroyed units;
- the Rally, All-out Attack and All-out Defence commands with command points;
- deployment territories, cover, blocking line of sight, objective control and
  end-of-turn scoring;
- one mission, two curated starter-army data packs, legal player actions with
  side ownership, automatic AI turns and an AI-vs-AI CLI regression harness.

Deliberately deferred for now: priority rolls, battle-shock and other morale
mechanics (AoS 4th has no battle-shock step), spells, manifestations, battle
tactics, faction rules, difficult-ground movement penalties, per-model
coherency, roster import and the UI. The full matrix is in
[the AoS 4th slice](aos4-slice.md).

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
    factions/stormcast-starter.json
    factions/skaven-starter.json
    missions/contested-ground.json
  wh40k11/
    factions/...
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

## Player flow

### Setup

1. Choose the mission, starter force and AI aggression profile.
2. The mission supplies the board, terrain, objectives and deployment zones.
3. The AI army is deployed from the mission defaults.
4. In the default quick-play mode both armies start deployed. Manual deployment
   remains available and uses the same validated `deploy` actions as any client.

### Human turn

1. The player selects one of their units on the board.
2. Legal orders are listed and visualised by the play API; the player chooses
   one.
3. The engine validates and applies it, resolves dice and updates the event log.
4. The player continues until the phase or turn is ended.
5. During AI-turn combat, the play API pauses at each human fight pick without
   allowing the AI to act for the player's units.

### AI turn

1. The AI considers only legal actions owned by the AI side.
2. The utility policy scores them and records its reason for each pick.
3. The engine resolves the AI actions automatically until the human is needed
   again: the start of their turn or an alternating-combat pick.
4. Objectives, command points, casualties and victory points update as events
   resolve.

### Save and resume

1. The server caches active matches because a five-round state is large.
2. Versioned JSON export/import preserves games across restarts or devices.
3. Export files contain no rules text or proprietary datasets.

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
