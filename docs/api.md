# API Reference

This document lists the HTTP API exposed by the Flask backend (`api_server.py`). All endpoints are intended for local development and play-testing.

Base URL: `http://<host>:5000` (backend) or proxied behind nginx in docker compose.

Authentication: none (local dev only). The server is stateless for simulation flows; clients are expected to hold the initial `seed`, current `turn`, and `ai_units` when interacting with the stateless endpoints.

Endpoints

1. POST /api/load_roster

- Purpose: Accepts a multipart file upload and returns parsed BattleScribe roster JSON.
- Request: multipart/form-data with field `file` (the Battlescribe HTML export file).
- Response: 200 JSON `{ "units": [ ... parsed unit objects ... ] }` or 400/500 with `{ error: "..." }`.

2. POST /api/run_simulation

- Purpose: one-off simulator run for quick experiments.
- Request (JSON): `{ "units": [...], "turns": N, "seed": S }`.
- Units follow the same simplified shape used throughout the app (see architecture doc).
- Response: 200 JSON `{ "events": [ ... ] }` — a concatenation of events from each simulated AI turn.

3. Stateless simulation endpoints (current)

- POST `/api/session_stateless`

  - Purpose: initialize a client-managed stateless run. Accepts either a multipart `file` upload (BattleScribe HTML) or JSON body with `units` and optional `roll_mode` / `battleplan`. The server returns an initial `seed`, `battleplan` summary, a minimal `state` (turn, ai_units, ai_profiles, roll_mode), and a `proposed_placement` when a matching battleplan and zone bias exist.

  - Response: 200 JSON `{ "seed": <int>, "battleplan": {...}, "state": { "turn": <int>, "ai_units": [...], "ai_profiles": [...] , "roll_mode": "ai"|"player" }, "proposed_placement": ... }`.

- POST `/api/ai_turn_stateless`

  - Purpose: run a single deterministic AI turn derived from the provided `seed` and `turn` (client must provide `{ seed, turn, ai_units, roll_mode }`). The server derives a per-turn RNG from `seed:turn` so runs are deterministic when the client records the seed and state.

  - Response (AI mode): 200 JSON `{ "turn": <int>, "events": [...] }` where `events` contains aggression checks and `action_resolved` events.
  - Response (player roll_mode): 200 JSON `{ "turn": <int>, "events": [...], "pending_actions": [...] }` where the server includes a `roll_request` event and `pending_actions` describing requested dice for the client to roll and return.

- POST `/api/resolve_rolls_stateless`

  - Purpose: Resolve player-provided roll results for a paused turn in the stateless flow. Accepts `{ seed, turn, pending_actions, action_results }` and returns `{ ok: true, events: [...] }` containing `action_resolved` events built from the client-supplied roll results.

- POST `/api/remove_unit_stateless`

  - Purpose: remove a unit from the provided `ai_units` list (stateless convenience endpoint). Accepts `{ ai_units, unit_name, turn? }` and returns `{ ok: true, removed_unit, remaining_units, event }`.

Note: legacy sessionful `/api/session` endpoints were intentionally removed; the server now favors stateless client-driven workflows. Calls to legacy paths will return 404 with an explanatory payload.

Error responses

- 400: bad request (missing parameters)
- 404: session not found
- 500: server exception (error JSON includes `error` string)

Examples (stateless)

Create a stateless session via JSON

Request

POST /api/session_stateless

```json
{
  "units": [
    {
      "name": "Ironjaw Warboss",
      "models": 1,
      "wounds_per_model": 5,
      "attacks": 3,
      "aggression": "Aggressive",
      "keywords": ["Monster", "Hero"]
    }
  ],
  "roll_mode": "player"
}
```

Response (200)

```json
{
  "seed": 123456789,
  "battleplan": { "id": 1, "title": "First Blood (2021)", "deployment": "..." },
  "state": {
    "turn": 1,
    "ai_units": [{ "name": "Ironjaw Warboss", "aggression": "Aggressive" }],
    "ai_profiles": [
      /* parsed profiles */
    ],
    "roll_mode": "player"
  },
  "proposed_placement": {
    /* optional placement hints */
  }
}
```

Create a session via multipart/form-data (file upload)

Include the `file` field containing the exported Battlescribe HTML and an optional `roll_mode` form field.

Example curl (file upload)

```bash
curl -X POST -F "file=@roster.html" -F "roll_mode=player" http://localhost:5000/api/session_stateless
```

Run a single AI turn (stateless)

Request

POST /api/ai_turn_stateless

```json
{
  "seed": 123456789,
  "turn": 1,
  "ai_units": [{ "name": "Ironjaw Warboss", "aggression": "Aggressive" }],
  "roll_mode": "player"
}
```

Response (player mode)

```json
{
  "turn": 1,
  "events": [
    /* aggression_check events, other structured events */
  ],
  "pending_actions": [
    {
      "request_id": "1-0",
      "unit": "Ironjaw Warboss",
      "card": { "title": "Crush and Consume" },
      "initiative": 8,
      "behavior": "attack",
      "dice": { "count": 1, "sides": 6 }
    }
  ]
}
```

The client should then POST roll results to `/api/resolve_rolls_stateless` with the `pending_actions` and `action_results` payload.

Resolve roll results (stateless)

Request

POST /api/resolve_rolls_stateless

```json
{
  "seed": 123456789,
  "turn": 1,
  "pending_actions": [
    /* payload from ai_turn_stateless */
  ],
  "action_results": [{ "request_id": "1-0", "result": { "roll": 4 } }]
}
```

Response (200)

```json
{
  "ok": true,
  "events": [
    {
      "event": "action_resolved",
      "action_resolved": {
        "turn": 1,
        "unit": "Ironjaw Warboss",
        "card_title": "Crush and Consume",
        "initiative": 8,
        "behavior": "attack",
        "details": { "roll": 4 }
      }
    }
  ]
}
```

Notes

- The server intentionally removed sessionful `/api/session` endpoints and now favors stateless client-managed workflows. Calls to legacy sessionful paths will return 404 with an explanatory payload.

\*\*\* End of file
