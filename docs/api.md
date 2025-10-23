# API Reference

This document lists the HTTP API exposed by the Flask backend (`api_server.py`). All endpoints are intended for local development and play-testing.

Base URL: `http://<host>:5000` (backend) or proxied behind nginx in docker compose.

Authentication: none (local dev only). Sessions are identified by UUIDs returned on creation.

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

3. POST /api/session

- Purpose: create a new AI session. Accepts a BattleScribe file upload or a JSON body with `units`.
- Request options:
  - multipart/form-data with `file` and optional form field `roll_mode` ("ai" or "player").
  - application/json with `{ "units": [...], "roll_mode": "ai"|"player" }`.
- Response: 200 JSON `{ "session_id": "<uuid>", "state": { "turn": <int>, "ai_count": <int>, "roll_mode": "ai"|"player" } }`.

4. GET /api/session/<session_id>

- Purpose: return current session state.
- Response: 200 JSON `{ "turn": <int>, "ai_units": [{ name, aggression }], "ai_profiles": [...parsed units...], "log": [...events...], "roll_mode": "ai"|"player" }`.

5. POST /api/session/<session_id>/ai_turn

- Purpose: run a single AI turn for the session.
- Behavior: uses the session's `SoloSimulator` instance and returns a plain-text human-readable summary. It also appends structured events to the session `log` and sets `last_turn_events`.
- Response: 200 text/plain with a readable summary. Use GET `/api/session/<id>/last_turn` to obtain structured JSON events.

6. GET /api/session/<session_id>/last_turn

- Purpose: return structured events from the last AI turn.
- Response: 200 JSON `{ "turn": <int>, "events": [...] }`.

7. POST /api/session/<session_id>/remove_unit

- Purpose: remove an AI unit from the session (e.g., when killed by the player).
- Request (JSON): `{ "unit_name": "<exact unit name>" }`.
- Response: 
  - 200 JSON `{ "ok": true, "removed_unit": "<name>", "remaining_units": [{name, aggression}], "remaining_count": <int> }`.
  - 400 JSON `{ "error": "unit_name required" }` if unit_name is missing.
  - 404 JSON `{ "error": "session not found" }` if session doesn't exist.
  - 404 JSON `{ "error": "unit not found", "unit_name": "<name>" }` if unit doesn't exist in the session.
- Behavior: 
  - Removes the unit from the simulator's active units list.
  - Updates session's ai_units and ai_profiles.
  - Creates a log entry: `{ "event": "unit_removed", "turn": <int>, "unit_name": "<name>", "reason": "killed_by_player" }`.
  - Future AI turns will not include actions for the removed unit.

8. GET /api/session/<session_id>/log

- Purpose: paginated access to the session log.
- Query params: `page` (1-based, default 1), `size` (items per page, default 50).
- Response: 200 JSON `{ "turn": <sim.turn>, "page": <int>, "size": <int>, "total": <int>, "items": [...] }`.

8. POST /api/session/<session_id>/notes

- Purpose: save a free-form note for the session.
- Request (JSON): `{ "text": "..." }`.
- Response: 200 JSON `{ "ok": true, "note": { "text": "..." } }`.

9. GET /api/session/<session_id>/notes

- Purpose: list session notes.
- Response: 200 JSON `{ "notes": [ { text: "..." }, ... ] }`.

Future endpoints (planned)

- POST /api/session/<session_id>/resolve_rolls — accept player-provided roll results to complete a paused AI turn when `roll_mode == 'player'` (server-mediated flow).
- Endpoints for player unit CRUD (if server-side player modeling is added).

Error responses

- 400: bad request (missing parameters)
- 404: session not found
- 500: server exception (error JSON includes `error` string)

Examples

Create a session via JSON

Request

POST /api/session

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
  "session_id": "f9b2c7f0-6d2e-4a91-9a4b-1a2b3c4d5e6f",
  "state": { "turn": 1, "ai_count": 1, "roll_mode": "player" }
}
```

Create a session via multipart/form-data (file upload)

Include the `file` field containing the exported Battlescribe HTML and an optional `roll_mode` form field.

Example curl (file upload)

```bash
curl -X POST -F "file=@roster.html" -F "roll_mode=player" http://localhost:5000/api/session
```

Response: same as JSON example above.

Run a single AI turn (server-side)

Request

POST /api/session/<session_id>/ai_turn

Response

- This endpoint returns a plain-text human-readable summary. It also appends structured events to the session log. To obtain structured events, call GET `/api/session/<session_id>/last_turn`.

Sample structured event schema

Events added to the session `log` follow a loose schema used throughout the simulator. Clients should treat fields as optional but can expect these common shapes:

1. Aggression check event

```json
{
  "event": "aggression_check",
  "unit": "Giant",
  "aggression_check": true,
  "roll": 4,
  "modifier": 2,
  "total": 6,
  "target": 5
}
```

2. Action resolved event

```json
{
  "event": "action_resolved",
  "action_resolved": {
    "unit": "Giant",
    "card_title": "Crush and Consume",
    "initiative": "High",
    "behavior": "attack",
    "details": {
      "attacks": 6,
      "unsaved_wounds": 3,
      "defender_remaining_models": 2
    }
  }
}
```

3. No tactic available

```json
{ "event": "no_tactic_available", "text": "No tactics in pool for this turn" }
```

Pagination example (session log)

Request

GET /api/session/<session_id>/log?page=2&size=10

Response

```json
{
  "turn": 3,
  "page": 2,
  "size": 10,
  "total": 37,
  "items": [
    /* events 11..20 */
  ]
}
```

Error examples

400 Bad request

```json
{ "error": "no file provided" }
```

404 Not found

```json
{ "error": "session not found" }
```

500 Server error

```json
{ "error": "KeyError: something failed" }
```

Roll-mode: server vs player (guidance)

- When `roll_mode == 'ai'`: `POST /api/session/<id>/ai_turn` returns resolved events and the session `log` contains concrete resolution results (unsaved wounds, models removed, etc.). This is the current default flow.
- When `roll_mode == 'player'`: the server persists the preference. Two patterns are recommended for clients:

  1. Server-mediated roll requests (recommended for deterministic persistence):

     - `POST /api/session/<id>/ai_turn` returns events up to the first unresolved roll and includes a special `roll_request` event listing required dice (dice type, modifiers, target, reason).
     - Client performs the physical or UI roll and posts results to `POST /api/session/<id>/resolve_rolls` with a payload matching the roll_request IDs and rolled values.
     - Server processes the roll results and continues resolving the turn, appending final events to the session log and returning completed events.

  2. Client-resolved flow (simpler):
     - `POST /api/session/<id>/ai_turn` returns structured, unresolved action events.
     - Client performs rolls locally and may optionally POST a final resolved summary to a persistence endpoint (eg. `POST /api/session/<id>/persist_events`) if you want the server to store the final outcome.

Draft contract: POST /api/session/<session_id>/resolve_rolls

Request (JSON)

```json
{
  "rolls": [
    { "request_id": "r1", "value": 5 },
    { "request_id": "r2", "value": 1 }
  ]
}
```

Response (200)

```json
{
  "ok": true,
  "events": [
    /* final events appended to the session log for this turn */
  ]
}
```

Notes

- The current server persists `roll_mode` on session creation and returns it via GET `/api/session/<id>`.
- The `resolve_rolls` endpoint is a draft and is not yet implemented; the contract above is proposed for a future release.

\*\*\* End of file
