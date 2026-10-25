# Table companion

The table companion is the primary Sad Hammer experience. It directs the AI
army from unit profiles and doctrine while the player measures, moves and rolls
on a real tabletop. It knows nothing about the board.

```
/         Table companion
/digital  Digital board game (preserved)
/legacy   Original card prototype (unchanged)
```

## Flow

1. On first open the app asks for the enemy army: use the Skaven starter or
   import a roster as JSON. Your Stormcast starter loads in the background for
   the planner's hero targets and can be edited in the roster editor.
2. Set up the table, then roll off. Tell the app who has the first turn; the
   deployment hint covers Press, Support and Hold.
3. The battle screen shows the round and one primary action: **Start the AI
   turn**. If the AI won the roll, that is the first thing you do.
4. The AI turn runs one phase at a time — Hero, Movement, Shooting, Charge,
   Combat, End. Each step shows only that phase's cards, so you can resolve it
   on the table before continuing.
5. The end phase also lists the AI units: mark any you destroyed, then finish
   the AI turn. Next round's plan leaves them out.
6. Finishing the turn offers the next round. From round two on the screen
   assumes you take your turn first and start the AI turn when the AI's turn
   comes around.
7. The app requests one plan per round: both rosters, the round, the seed and
   the destroyed AI unit IDs. The rosters, round, destroyed units, first turn
   and current AI phase are stored in localStorage.

## Rosters

A roster is a name, a faction and a list of units. The builder edits both
slots; **Swap sides** exchanges them.

```json
{
  "name": "My Stormcast",
  "faction": "Stormcast Eternals",
  "units": [
    {
      "id": "liberators",
      "name": "Liberators",
      "move": 5,
      "save": 3,
      "health": 2,
      "models": 10,
      "control": 1,
      "keywords": ["Infantry", "Stormcast Eternals", "Order"],
      "weapons": [
        {
          "name": "Liberator hammer",
          "range": 0,
          "attacks": 2,
          "hit": 3,
          "wound": 3,
          "rend": 1,
          "damage": 1
        }
      ]
    }
  ]
}
```

Rules:

- `id` is optional on import. The server derives it from the name and suffixes
  duplicates (`clanrats`, `clanrats-2`), so destroyed toggles and seeded
  variation stay stable.
- `range` 0 means melee; any positive range is a ranged weapon.
- `keywords` are free text. `Hero`, `Hold` or `Defensive` puts a unit in the
  Hold doctrine.
- Numeric strings (`"save": "3"`) are accepted on import and canonicalised.
- Points, roles and other extra keys are ignored.
- There are no list-building restrictions. Structural limits are 40 units per
  roster, 12 weapons and 24 keywords per unit, and at least one weapon per
  unit.

### Starters

`GET /api/table/rosters` returns the curated Stormcast and Skaven starter
rosters, read from the same faction packs as the digital game. The default
slots are Stormcast for the player and Skaven for the AI. The planner runs on
the local backend; no third-party roster or game service is used.

### Storage

| localStorage key | Contents |
| --- | --- |
| `sadhammer.table.rosters` | Both rosters, including the current swap |
| `sadhammer.table.session` | Seed, round, destroyed AI unit IDs, enemy-ready flag, first turn and the AI turn's current phase |

A reload mid-turn resumes at the same phase. A session from an earlier version
of the app keeps its saved rosters and resumes at the first-turn step.

Clearing site data restores the starters on the next load.

## Doctrine

Classification is profile-only, in this order:

1. **Hold** — a `Hero`, `Hold` or `Defensive` keyword. Heroes stay with the
   line even when they carry a ranged weapon.
2. **Support** — a non-hero unit with at least one ranged weapon.
3. **Press** — everything else.

| Phase | Press | Support | Hold |
| --- | --- | --- | --- |
| Hero | — | — | Use the warscroll or command ability to support the nearest friendly unit within 12" |
| Movement | Full advance; advance into cover; push an objective | Hold in cover; reposition for line of sight; fall back; line up the closest enemy Hero | Support the nearest friendly unit; hold an objective; move to cover near an objective |
| Shooting | — | Shoot from cover, after repositioning or falling back, or focus the closest enemy Hero | — |
| Charge | Charge if the closest enemy is within 12" | Do not charge unless there is no shooting target and an enemy is already within 6" | Do not charge |
| Combat | Fight the closest engaged enemy | Fight only if already engaged | Fight only if already engaged |
| End | Score objectives; remove destroyed units, mark AI losses and advance the round | | |

The Support movement choice also selects the shooting instruction, so a unit
that falls back shoots after falling back and a unit that lines up a Hero
focuses its shooting on that Hero. The "focus the closest enemy Hero" option is
only available when the player roster contains a Hero.

Every instruction is relative. The planner never returns positions,
coordinates, distances to a fixed point, terrain geometry or wound state.

## Seeded variation

The plan is deterministic:

- the same rosters, round, seed and destroyed list return the same plan;
- the maneuver index is `hash(seed, unit_id, phase) + round - 1`, modulo the
  number of options for that unit;
- consecutive rounds therefore rotate through the options rather than
  repeating, and different seeds start units at different points in the
  rotation.

There is no player-facing aggression, difficulty or AI-style choice.

## HTTP API

All table routes are stateless and JSON-only. They are registered under
`/api/table` and never touch the digital game store.

### `GET /api/table/rosters`

Abridged below; the real response contains every starter unit and weapon.

```json
{
  "rosters": {
    "stormcast-starter": { "name": "Stormcast Eternals", "faction": "Stormcast Eternals", "units": [] },
    "skaven-starter": { "name": "Skaven", "faction": "Skaven", "units": [] }
  },
  "defaults": { "player": "stormcast-starter", "ai": "skaven-starter" },
  "doctrines": { "press": "Press", "support": "Support", "hold": "Hold" }
}
```

### `POST /api/table/rosters/validate`

The request body is a roster object. A valid roster returns its canonical form;
an invalid one returns `400` with field-level issues.

```json
{
  "roster": {
    "name": "My roster",
    "faction": "Order",
    "units": [
      {
        "id": "clanrats",
        "name": "Clanrats",
        "move": 5,
        "save": 5,
        "health": 1,
        "models": 10,
        "control": 1,
        "keywords": ["Infantry"],
        "weapons": [
          {
            "name": "Rusty blade",
            "range": 0,
            "attacks": 2,
            "hit": 4,
            "wound": 4,
            "rend": 0,
            "damage": 1
          }
        ]
      }
    ]
  }
}
```

```json
{
  "error": "the roster is not valid",
  "issues": [
    { "field": "roster.units[0].save", "message": "roster.units[0].save must be at least 2" }
  ]
}
```

### `POST /api/table/plan`

```json
{
  "player_roster": { "name": "Stormcast Eternals", "units": [] },
  "ai_roster": { "name": "Skaven", "units": [] },
  "round": 1,
  "seed": 42,
  "destroyed": ["clanrats"]
}
```

`round` is 1–20, `seed` is 0–2147483647 and `destroyed` is an array of AI unit
IDs or names. Unknown destroyed entries are ignored.

```json
{
  "round": 1,
  "seed": 42,
  "player_roster": { "name": "Stormcast Eternals", "faction": "Stormcast Eternals", "unit_count": 5 },
  "ai_roster": {
    "name": "Skaven",
    "faction": "Skaven",
    "unit_count": 6,
    "active_count": 5,
    "destroyed": ["clanrats"]
  },
  "units": [
    {
      "id": "grey-seer",
      "name": "Grey Seer",
      "doctrine": "hold",
      "doctrine_label": "Hold",
      "doctrine_reason": "Hero — supports the line and holds ground."
    }
  ],
  "phases": [
    {
      "id": "hero",
      "name": "Hero phase",
      "instructions": [
        {
          "phase": "hero",
          "unit_id": "grey-seer",
          "unit_name": "Grey Seer",
          "doctrine": "hold",
          "maneuver": "support_ability",
          "maneuver_name": "Lead from the line",
          "instruction": "Use this unit's warscroll or command ability to support the nearest friendly unit within 12 inches.",
          "reason": "Hero phase — buffs and commands come before movement.",
          "weapons": []
        }
      ]
    }
  ]
}
```

Phases always appear in this order: `hero`, `movement`, `shooting`, `charge`,
`combat`, `end`. End-phase instructions have `unit_id: null` and are general
table housekeeping. Weapon profiles are attached in the shooting phase
(ranged weapons only) and the combat phase (melee weapons only).

Errors follow the same shape as the rest of the app:

```json
{ "error": "round must be between 1 and 20" }
```

Invalid rosters add an `issues` array. Missing rosters, invalid round/seed or a
malformed destroyed list return `400`; a starter data failure returns `500`.

## Verification

```bash
pytest tests/test_table_rosters.py tests/test_table_planner.py tests/test_table_api.py -q
cd frontend && npm run build
```

The tests cover roster parsing and IDs, doctrine classification (including
ranged heroes and defensive keywords), Support charge/shoot constraints, seeded
determinism and rotation, destroyed-unit filtering, and the HTTP contracts.
