# Placement suggestion schema

This document describes the JSON shape returned by the server for placement suggestions.

Required top-level fields (returned by GET `/api/session/<id>/placement` as `placement`):

- event: string — must be "placement"
- turn: integer — the turn the placement applies to (usually 1)
- battleplan: object|null — optional battleplan information (id, title)
- allowed_zones: array[string] — names of allowed deployment zones for this battleplan
- suggestions: array[object] — per-unit placement suggestions

Each suggestion object contains at minimum:

- unit: string — unit name
- suggested_zone: string|null — suggested canonical zone (left/center/right/forward/defensive/reserve/scattered)
- scores: object — mapping of zone -> numeric score
- reason: string — short explanation for the suggestion

Optional hint fields (helpful for frontends):

- priority: "High"|"Medium"|"Low"
- zone_hint: string — short text to show under the unit name
- distance_range: "small"|"medium"|"deep" — rough deployment depth
- coordinate_hint: string — natural-language positional hint (e.g., "Near the left table edge")

See `placement_schema.json` for a machine-readable JSON Schema (draft-07).
