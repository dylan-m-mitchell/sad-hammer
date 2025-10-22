# Rule mapping: Accurate fidelity (Generals Handbook 2021)

This document outlines how Sad Hammer's Solo AI maps to Age of Sigmar (GH2021) mechanics when running in `Accurate` fidelity mode.

Goals

- Provide a practical AI opponent that follows GH2021 intent and Peter Holland's solo wargaming notes.
- Keep the simulator usable at the table: return clear human-readable prompts, but preserve deterministic logs for reproducibility and debugging.

Scope — what the app simulates (server-side)

- Turn sequencing: battle round, AI turn only (player turn is enacted by the human — server does not enforce movement rules unless in `Auto` mode).
- Aggression checks: implemented as d6 + unit modifiers >= target, where target is mapped from Aggression (Aggressive/Neutral/Cautious) per GH2021 guidance.
- Tactic selection and action draws: follows the card decks in `reference_card_decks.py` and the blog's pool rules (Broken Ranks added turn 2, etc.).
- Action resolution summary: server returns structured events (aggression_check, action_resolved) but does not resolve full AoS attack-to-wound-roll-by-roll unless `Accurate` combat mode is enabled.

Scope — what the app does NOT simulate (left to the human at the table)

- Exact positioning, movement distances, line-of-sight and terrain-dependent rules.
- Full rulebook subtleties like advanced sequences for specific artefacts or layered abilities that require board context.

Accurate fidelity behavior (what changes compared to MVP)

- Combat resolution: when an action indicates an attack, the simulator performs full roll-by-roll resolution using weapon profiles (to-hit/to-wound/rend/damage) and updates unit wounds and models.
- Morale / battleshock: simple battleshock rules implemented (leadership check adjusted by casualties), with thresholds and rout handling consistent with GH2021 simplifications.
- Unit profiles: parsed from BattleScribe HTML when available (wounds_per_model, attacks, weapons). Missing fields use safe defaults.
- Deterministic seeds: acceptance tests and debugging runs use RNG seeding to reproduce runs.

Acceptance tests (examples)

1. Aggression & modifier test

   - Input: single AI unit Aggressive, modifier +2, seed fixed
   - Expected: d6 + 2 meets or exceeds the Aggressive threshold on the deterministic roll sequence (documented in tests)

2. Tactic pool evolution

   - Input: initial tactic pool; simulate 3 turns
   - Expected: Broken Ranks added on turn 2 and remaining tactics added on turn 3; no duplicates in pool/discard behavior.

3. Action resolution with accurate combat

   - Input: AI action behavior includes 'attack'; attacker profile: 3 models, 1 attack each, to_hit 4+, to_wound 4+, damage 1; defender: 5 models, 1 wound each, save 6+
   - Expected: deterministic number of unsaved wounds with given seed; defender models reduced accordingly.

4. Battleshock handling
   - Input: after combat, defender lost X models; check for battleshock threshold and verify pass/fail behavior with seeded rolls.

Where to find related code

- `full_simulator.py` — tactic selection, aggression checks, action drawing.
- `interactive_simulator.py` — unit state, combat resolution helpers for the Accurate mode.
- `battlescribe_parser.py` — roster parsing and weapon profile extraction.

Next actions

- Implement acceptance tests in `tests/` (pytest) with deterministic seeds.
- Wire an `--fidelity accurate` flag to `run_simulation` so the simulator switches to accurate combat resolution.

Roll handling modes

Sad Hammer now supports a per-session `roll_mode` that controls who performs/records the AI's dice rolls:

- `ai` (default): the server performs all dice rolls during `ai_turn` and returns fully-resolved events (human-readable text and structured JSON). This is the simplest and most automated mode for players who want the AI opponent to be self-contained.

- `player`: the session is flagged so the player resolves the AI's rolls at the table. The server persists the `roll_mode` but currently still executes turns server-side; see Recommended behaviors below for how to evolve the server/client contract if you prefer a server-mediated roll-request flow.

Recommended behaviors

- Server-mediated roll requests (server-assisted player resolution): when `roll_mode == 'player'`, the server should return structured events that include explicit roll requests (which die to roll, what modifiers/targets apply) and pause resolution. The client performs the die roll physically (or with a client-side RNG) and POSTs the roll result back to an endpoint (eg. `POST /api/session/<id>/resolve_rolls`) so the server can finish resolving effects and persist the final events to the session log. This preserves determinism when players record the exact roll values.

- Client-resolved flow (simpler): the server returns structured, but unresolved, action events when in `player` mode and the client performs all rolls locally and applies resolution in the UI. The client can optionally call endpoints to persist the final outcome if desired (eg. POST the final resolved events or resulting unit state).

- UX tip: show clear roll prompts in the UI (which unit, which roll, modifiers, and the target) and provide a simple numeric input or an on-screen die that the player can tap to record the rolled value.

Implementation note

- The repo now persists `roll_mode` on session creation and returns it in the session state. Tests were added to assert this behavior. The next incremental enhancement is to implement the server-mediated roll-request flow and an accompanying small API to accept roll results and complete a paused AI turn.
