# Remove Unit Feature

This feature allows players to remove AI units from active play when they are eliminated during the game.

## Overview

When playing against the AI, the player may kill or destroy AI units during combat. This feature provides an API endpoint to remove those units from the simulation, ensuring that:

- Subsequent AI turns only generate actions for surviving units
- The session log records which units were removed and when
- The game state accurately reflects casualties on the battlefield

## API Endpoint

### `POST /api/session/<session_id>/remove_unit`

Remove an AI unit from the session.

**Request Body (JSON):**
```json
{
  "unit_name": "Exact Unit Name"
}
```

**Success Response (200):**
```json
{
  "ok": true,
  "removed_unit": "Exact Unit Name",
  "remaining_units": [
    {"name": "Unit A", "aggression": "Aggressive"},
    {"name": "Unit B", "aggression": "Neutral"}
  ],
  "remaining_count": 2
}
```

**Error Responses:**

- `400`: Missing `unit_name` field
- `404`: Session not found
- `404`: Unit not found in the session

## Event Logging

When a unit is removed, the following event is added to the session log:

```json
{
  "event": "unit_removed",
  "turn": 3,
  "unit_name": "Huskard on Stonehorn",
  "reason": "killed_by_player"
}
```

## Usage Example

### Python (using requests)

```python
import requests

session_id = "your-session-id"
unit_to_remove = "Mournfang Pack A"

response = requests.post(
    f"http://localhost:5000/api/session/{session_id}/remove_unit",
    json={"unit_name": unit_to_remove}
)

if response.status_code == 200:
    result = response.json()
    print(f"Removed: {result['removed_unit']}")
    print(f"Remaining: {result['remaining_count']} units")
else:
    print(f"Error: {response.json()['error']}")
```

### JavaScript (fetch)

```javascript
const sessionId = 'your-session-id';
const unitName = 'Mournfang Pack A';

fetch(`http://localhost:5000/api/session/${sessionId}/remove_unit`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ unit_name: unitName })
})
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      console.log(`Removed: ${data.removed_unit}`);
      console.log(`Remaining: ${data.remaining_count} units`);
    } else {
      console.error(`Error: ${data.error}`);
    }
  });
```

### cURL

```bash
curl -X POST http://localhost:5000/api/session/YOUR_SESSION_ID/remove_unit \
  -H "Content-Type: application/json" \
  -d '{"unit_name": "Mournfang Pack A"}'
```

## Implementation Details

### Backend Changes

1. **`full_simulator.py`**: Added `remove_unit(unit_name)` method to `SoloSimulator` class
   - Returns `True` if unit was found and removed
   - Returns `False` if unit doesn't exist
   - Removes unit from `self.units` list

2. **`api_server.py`**: Added `POST /api/session/<session_id>/remove_unit` endpoint
   - Validates request payload
   - Removes unit from simulator
   - Updates session's `ai_units` and `ai_profiles` lists
   - Logs removal event to session log
   - Returns updated unit list

### Testing

The feature includes comprehensive test coverage:

- **7 unit tests** (`tests/test_remove_unit.py`):
  - Remove existing unit
  - Remove nonexistent unit
  - Remove all units sequentially
  - Remove first/last units
  - Simulator continues after removal
  - Case-sensitive matching

- **7 API tests** (`tests/test_api_remove_unit.py`):
  - Successful removal
  - Unit not found error
  - Missing unit_name error
  - Session not found error
  - Event logging
  - Multiple sequential removals
  - AI turn after removal

All tests pass ✓

## Frontend Integration

To integrate this feature into the frontend:

1. **Add a "Remove Unit" button** for each AI unit in the UI
2. **Call the API** when the button is clicked
3. **Update the UI** to reflect the remaining units
4. **Display feedback** to confirm the removal

Example UI flow:
```
[AI Unit: Mournfang Pack A] [❌ Remove]
↓ (player clicks Remove)
POST /api/session/{id}/remove_unit
↓ (success)
Unit removed from UI
Update unit count display
Continue with remaining units
```

## Game State Consistency

The feature ensures consistency across three layers:

1. **Simulator state** (`sim.units`): Active units for AI logic
2. **Session state** (`sess['ai_units']`): Simplified unit references
3. **Session profiles** (`sess['ai_profiles']`): Full parsed unit data

All three are updated atomically when a unit is removed.

## Future Enhancements

Potential improvements for future releases:

- Batch removal (remove multiple units at once)
- Undo/restore removed units
- Partial casualties (reduce model count within a unit)
- Removal reasons (killed, fled, summoned away, etc.)
- Front-end confirmation dialog
- Animation/visual effects for unit removal

## See Also

- [API Documentation](../docs/api.md)
- [Example Script](../scripts/example_remove_unit.py)
- [Architecture Overview](../docs/architecture.md)
