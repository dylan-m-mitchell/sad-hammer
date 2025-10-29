# Remove Unit Feature

This feature allows players to remove AI units from active play when they are eliminated during the game.

## Overview

When playing against the AI, the player may kill or destroy AI units during combat. This feature provides an API endpoint to remove those units from the simulation, ensuring that:

- Subsequent AI turns only generate actions for surviving units
- The session log records which units were removed and when
- The game state accurately reflects casualties on the battlefield

## API Endpoint

### `POST /api/remove_unit_stateless`

Stateless removal: the client sends the current list of AI units and the unit name to remove.

**Request Body (JSON):**

```json
{
  "ai_units": [ { "name": "Mournfang Pack A", "aggression": "Aggressive" }, ... ],
  "unit_name": "Exact Unit Name",
  "turn": 3  // optional: provide current turn for deterministic behavior if needed
}
```

**Success Response (200):**

```json
{
  "ok": true,
  "unit_removed": "Exact Unit Name",
  "remaining_units": [
    { "name": "Unit A", "aggression": "Aggressive" },
    { "name": "Unit B", "aggression": "Neutral" }
  ],
  "remaining_count": 2
}
```

**Error Responses:**

- `400`: Missing `unit_name` field
- `404`: Session not found

````markdown
# Remove Unit Feature (stateless)

This feature lets a client remove AI units from the game in a stateless way.
The server does not persist sessions — the client is responsible for holding the
current AI unit list (and the initial seed/turn when running deterministic turns).

## Overview

When the player kills an AI unit, the client should call the stateless removal
endpoint and then update its local state (ai_units). Subsequent calls to
`/api/ai_turn_stateless` should use the updated ai_units list so the AI only
generates actions for surviving units.

## API Endpoint

### `POST /api/remove_unit_stateless`

Stateless removal: the client sends the current list of AI units and the unit
name to remove. The server returns the remaining units and an event describing
the removal. The server does not store or mutate any server-side session.

Request Body (JSON):

```json
{
  "ai_units": [ { "name": "Mournfang Pack A", "aggression": "Aggressive" }, ... ],
  "unit_name": "Exact Unit Name",
  "turn": 3
}
```

Success Response (200):

```json
{
  "ok": true,
  "removed_unit": "Exact Unit Name",
  "remaining_units": [
    { "name": "Unit A", "aggression": "Aggressive" },
    { "name": "Unit B", "aggression": "Neutral" }
  ],
  "event": {
    "event": "unit_removed",
    "turn": 3,
    "unit_name": "Exact Unit Name",
    "reason": "killed_by_player"
  }
}
```

Error Responses:

- `400`: Missing `unit_name` field

Note: because the endpoint is stateless the server will not return 404 for a
missing session — the client should provide the ai_units list it believes to be
current. If a unit name is not present in the provided list, the server will
still return a 200 response with the same remaining_units (no-op) and the
event will indicate the attempted removal.

## Usage Examples

### Python (using requests)

```python
import requests

ai_units = [
  {"name": "Mournfang Pack A", "aggression": "Aggressive"},
  {"name": "Huskard on Stonehorn", "aggression": "Aggressive"}
]
unit_to_remove = "Mournfang Pack A"

response = requests.post(
  "http://localhost:5000/api/remove_unit_stateless",
  json={"ai_units": ai_units, "unit_name": unit_to_remove, "turn": 2}
)

if response.status_code == 200:
  result = response.json()
  print(f"Removed: {result['removed_unit']}")
  print(f"Remaining: {len(result['remaining_units'])} units")
else:
  print(f"Error: {response.status_code} {response.text}")
```

### JavaScript (fetch)

```javascript
const aiUnits = [
  { name: "Mournfang Pack A", aggression: "Aggressive" },
  { name: "Huskard on Stonehorn", aggression: "Aggressive" },
];
const unitName = "Mournfang Pack A";

fetch("http://localhost:5000/api/remove_unit_stateless", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ ai_units: aiUnits, unit_name: unitName, turn: 2 }),
})
  .then((res) => res.json())
  .then((data) => {
    if (data.ok) {
      console.log(`Removed: ${data.removed_unit}`);
      console.log(`Remaining: ${data.remaining_units.length} units`);
    } else {
      console.error(`Error: ${JSON.stringify(data)}`);
    }
  });
```

### cURL

```bash
curl -X POST http://localhost:5000/api/remove_unit_stateless \
  -H "Content-Type: application/json" \
  -d '{"ai_units": [{"name":"Mournfang Pack A","aggression":"Aggressive"}], "unit_name": "Mournfang Pack A", "turn": 2}'
```

## Implementation Notes

- The endpoint `POST /api/remove_unit_stateless` is implemented in `api_server.py`.
- It expects an `ai_units` array and `unit_name`. It computes the remaining
  units from the provided list and returns an event describing the removal.
- The server does not persist or mutate sessions — the client must keep the
  canonical list of ai_units and the initial seed/turn when performing
  deterministic AI turns via `/api/ai_turn_stateless`.

## Testing

- API tests for this endpoint live in `tests/test_api_remove_unit_stateless.py`.
  They cover successful removal and missing `unit_name` error cases. Tests are
  written to expect the stateless behavior (server returns `removed_unit` and
  `remaining_units`, and does not rely on a server-side session).

## Frontend Integration

1. Keep a client-side representation of the AI units (an array of unit objects).
2. When the player removes a unit, call `POST /api/remove_unit_stateless` with
   the current ai_units and unit_name.
3. Use the returned `remaining_units` to update the client UI and local state.
4. When requesting AI turns afterwards, pass the updated `ai_units` and the
   same initial `seed` (and updated `turn`) to `/api/ai_turn_stateless` so the
   server computes deterministic actions for the survivors.

Example UI flow (stateless):

```
[AI Unit: Mournfang Pack A] [❌ Remove]
↓ (player clicks Remove)
POST /api/remove_unit_stateless with current ai_units
↓ (success)
Update client ai_units from response.remaining_units
Update UI counts and continue
```

## Future Enhancements

- Batch removal (remove multiple units at once)
- Undo/restore removed units (client-side only, or via a separate restore API)
- Partial casualties (reduce model count within a unit)
- More structured removal reasons

## See Also

- [API Documentation](../docs/api.md)
- [Example Script](../scripts/example_remove_unit.py)
- [Architecture Overview](../docs/architecture.md)
````
