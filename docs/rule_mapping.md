# Rule mapping: Accurate fidelity (Generals Handbook 2021)

This document outlines how Sad Hammer's Solo AI maps to Age of Sigmar (GH2021) mechanics when running in `Accurate` fidelity mode.

Goals

- Provide a practical AI opponent that follows GH2021 intent and Peter Holland's solo wargaming notes.
- Keep the simulator usable at the table: return clear human-readable prompts, but preserve deterministic logs for reproducibility and debugging.

Scope — what the app simulates (server-side)

- Turn sequencing: battle round, AI turn only (player turn is enacted by the human — the server does not enforce movement rules unless an automated mode is explicitly wired in).
- Aggression checks: implemented as d6 + unit modifiers >= a target threshold mapped from Aggression (Aggressive/Neutral/Cautious).
- Tactic selection and action draws: follows the card decks in `reference_card_decks.py` and the Solo Wargaming deck rules (cards may be added to the pool on specified turns).
- Action resolution: the server returns structured events (aggression_check, action_resolved). A separate, simplified combat harness (`interactive_simulator.py`) can perform roll-by-roll attack resolution for testing/play but it is not a full rulebook-accurate engine — many AoS subtleties (pile-in, consolidation, line-of-sight, detailed ability interactions) are intentionally simplified or not modeled.
- Battleshock / morale: not implemented as a full system in the server; current tests include placeholders for morale/battleshock behavior. If accurate morale is required, it should be added to the combat resolution harness.
- Unit profiles: parsed from BattleScribe HTML when available (wounds_per_model, attacks, weapons). Missing fields use conservative defaults in the combat harness.
- Deterministic seeds: the stateless API derives per-turn seeds from the initial seed to allow deterministic replays when clients persist the seed and state.
- Exact positioning, movement distances, line-of-sight and terrain-dependent rules.
- Full rulebook subtleties like advanced sequences for specific artefacts or layered abilities that require board context.

Accurate fidelity behavior (what changes compared to MVP)

- Combat resolution (current state): `interactive_simulator.py` contains a simplified roll-by-roll resolution helper (`resolve_attack`) used in demos and tests. This harness models to-hit, to-wound, save, and simple damage profiles (including D-sides), but it does not implement full AoS sequencing (pile-in, consolidation, overlapping abilities, or extensive special rules).
- Morale / battleshock: currently a placeholder in tests; a full battleshock implementation is not present in the simulator and should be added if required for Accurate mode.
- Unit profiles: parsed from BattleScribe HTML when available and used by the simplified combat harness; missing attributes fall back to conservative defaults.
- Deterministic seeds: acceptance tests and debugging runs use deterministic RNG seeding; the stateless API derives a per-turn seed to preserve repeatability when clients persist the initial seed and turn index.

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
