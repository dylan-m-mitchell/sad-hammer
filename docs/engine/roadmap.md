# Engine roadmap

This roadmap replaces the earlier “finish the card prototype” plan. The target
is a player-facing game that opens on mobile or web, lets a human play a quick
battle against an explainable AI, and ships edition-specific rules for Age of
Sigmar 4th and Warhammer 40,000 11th. AI-vs-AI play is an engine test harness,
not the product goal.

## Guiding decisions

- **Interfaces first, one complete slice second.** The shared contracts are
  small and proven by the demo system; the next milestone implements AoS 4th
  fully through those contracts before starting 40k.
- **No universal card engine.** Each edition owns its phases, combat, morale,
  mission scoring and resources. Battle tactics may be mission data, not a
  turn driver.
- **Player authority, engine resolution.** The player issues orders on a digital
  board. The engine validates them, resolves dice and updates the shared state;
  the same action contract drives the AI. Optional physical-table mirroring is a
  later enhancement, not a prerequisite.
- **Terrain and deployment are part of v1.** Terrain affects line of sight,
  cover, movement and therefore AI decisions. Both editors must work before the
  game is considered feature-complete.
- **AI must be legal, explainable and characterful.** Utility scoring over
  system-enumerated actions; the product uses one fixed, server-owned balanced
  opponent while internal profiles support testing; no machine learning or LLM.
- **Save/export from day one.** The canonical state is versioned JSON. Active
  games are cached server-side by game id; export/import keeps them portable and
  recoverable after a restart.
- **Rules content stays out of the repository.** Commit links, summaries and
  structured data, not PDFs or copied rulebook text.

## Current branch

Phase 0 and the Phase 1 walking skeleton are merged to `main`. The
`feature/aos4-vertical-slice` branch now contains the AoS 4th rules module, the
two starter data packs, the contested-ground mission, the AoS CLI, the play API
and the player-facing React game. The legacy card simulator remains on `main`
and stays reachable at `/legacy` while the new game becomes the default
experience.

## Phase 0 — Foundation

**Goal:** remove product ambiguity and make the architecture executable.

- [x] Lock editions, player model, deployment scope and roster workflow.
- [x] Verify the official free core-rules PDFs are downloadable.
- [x] Define the `GameSystem`, `GameState`, action and event contracts.
- [x] Define a versioned serialization strategy.
- [x] Define the utility-AI and aggression-profile model.
- [x] Document rules references, scope and legal constraints.
- [x] Create the feature branch and focused CI plan.

**Exit criteria:** another contributor can read the docs and add a rules module
without reverse-engineering the legacy simulator.

## Phase 1 — Core engine walking skeleton

**Goal:** prove determinism, serialization, validation, legal actions, AI
selection and the turn loop independently of either commercial ruleset.

- [x] Deterministic dice from a seed and serializable cursor.
- [x] Board, polygon terrain, objectives, units, weapons and deployment zones.
- [x] Versioned state with structural validation.
- [x] Event log stamped with sequence, round, phase and side.
- [x] `GameSystem` abstract interface and an action/result contract.
- [x] Demo movement/shooting system with one objective and phase transitions.
- [x] Utility AI with internal profiles, alternatives and explanations.
- [x] CLI demo, save/load and inspect commands.
- [x] Focused engine tests and CI workflow.

**Exit criteria met by the demo:** two armies, a board, terrain, objective,
legal moves and attacks, AI turns, deterministic replay and JSON round-trip.

## Phase 2 — AoS 4th vertical slice

**Goal:** one complete, played-through AoS 4th game with the Skaventide starter
forces, one mission and the core rules.

- [x] Rules matrix: phases, core abilities, combat sequence, wards, terrain,
      objective control and battle-round scoring.
- [x] Data packs for a curated Stormcast Eternals force and a curated Skaven
      force from the starter set.
- [x] Deployment phase: territories, objectives, units, terrain and validation.
- [x] Start of Turn, Hero, Movement, Shooting, Charge, Combat and End of Turn.
- [x] Normal Move, Run, Retreat, Shoot, Charge and Fight.
- [x] Weapon attacks, hit/wound/save/damage, mortal damage, wards and
      destroyed units.
- [x] One mission with end-of-turn objective scoring and a battle-round limit.
- [x] AI v1 using the generic policy and AoS-specific evaluation, including
      objective-value/control and retaliation-risk scoring.
- [x] Headless `aos4-bench` AI-vs-AI benchmark for tuning and regression.
- [x] Rules tests for every implemented core interaction plus an AI-vs-AI
      regression game and CLI smoke test.

The implemented rules and the deliberate simplifications are listed in
[the AoS 4th slice](aos4-slice.md). In particular, AoS 4th has no battle-shock
step; bravery is retained in the data model for future morale work.

**Exit:** the AoS game can be played end-to-end against the AI through the engine
and web client with legal, explainable decisions. This is the first real proof
that the abstraction works.

## Phase 3 — Player-facing web game

**Goal:** open the app on a phone or in a browser and play a quick AoS 4th game
against the AI.

- [x] One-click default game with optional mission/force/seed customization and
      a fixed, server-owned opponent.
- [x] Responsive SVG board with terrain, objectives, deployment zones and units.
- [x] Legal order UI for deployment, movement, shooting, charges, combat and
      commands.
- [x] Automatic AI turns with an explainable intent log.
- [x] Alternating combat picks with strict side ownership.
- [x] Battle log, scores, command points, phase and round status.
- [x] Result flow with rematch, new battle, export and review.
- [x] JSON export/import and in-browser save resume.
- [x] Mobile/tablet layout for the complete game loop.
- [ ] Editable terrain layout and a richer drag-and-drop deployment editor.
- [ ] Per-action animation, undo and replay controls.
- [ ] Accessibility audit and keyboard-first board controls.

**Exit:** a player can open the app, start a battle and complete a legal,
enjoyable AoS game against the AI without using the CLI. **Met for the AoS
slice.**

## Phase 4 — AI quality

**Goal:** make the opponent feel like a player rather than a score maximizer.

- [ ] Mission planning: hold, contest, screen, trade and deny.
- [ ] Threat map based on damage range, melee threat, objective pressure and
      remaining durability.
- [ ] Target priority and risk assessment.
- [ ] Per-unit aggression and personality with global difficulty presets.
- [ ] Seeded variation so two games with the same opening are not identical.
- [ ] Decision explanations in the UI and a replayable “why” log.
- [ ] AI-vs-AI batch runs, illegal-action assertions and balance dashboards.

**Exit:** experienced players describe the AI as predictable in intent but not
trivially exploitable.

## Phase 5 — Warhammer 40,000 11th

**Goal:** the same player-facing game flow for 40k 11th.

- [ ] Rules matrix for 11th edition: battle round, player turns, seven steps,
      Command CP, battle-shock, movement, shooting, charge, fight, end of turn.
- [ ] Curated Armageddon Space Marines and Orks data packs.
- [ ] One mission from the current mission deck.
- [ ] Command-point and stratagem subset; mission scoring.
- [ ] AI policy hooks for CP spending and threat ranges.
- [ ] Shared UI with system-specific controls and phase labels.
- [ ] Cross-system tests proving the core did not become AoS-shaped.

**Exit:** a complete 40k game through the same browser flow with a legal AI.

## Phase 6 — Roster workbench

**Goal:** workable rosters without BattleScribe.

- [ ] New Recruit `.ros`/`.rosz` import with clear unknown-unit diagnostics.
- [ ] Curated builder for supported factions, including wargear and points.
- [ ] `.ros` export for interoperability.
- [ ] Data-pack versioning and validation.
- [ ] Legacy BattleScribe HTML import kept as a fallback only.

**Exit:** a player can create or import a legal list for every supported starter
faction without external desktop software.

## Phase 7 — Hardening and release

- [ ] Complete tests, formatting and lint gates.
- [ ] API contract tests and stateless-state size checks.
- [ ] Save migrations and backward-compatibility policy.
- [ ] Packaging, container images, sample games and onboarding docs.
- [ ] Performance pass for AI enumeration on full-size boards.
- [ ] Licensing review and contributor data policy.
- [ ] Tagged release.

## Dependency order

```text
Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 4
                         |            |
                         +-> Phase 5 -+
Phase 6 can start once data-pack schemas stabilize, in parallel with Phase 2/5.
```

Phase 5 should not start before Phase 2 is playable. Building both rules modules
from the same abstraction before either is proven is the main over-abstraction
risk. Phase 6 can start earlier because roster data is largely independent.

## Near-term sequence

1. Merge the engine foundation and get the focused CI green. **Done.**
2. Build the AoS 4th rules matrix and the two starter data packs. **Done.**
3. Implement deployment, movement, shooting, charge, combat and one mission.
   **Done.**
4. Play an AI-vs-AI AoS game and fix rules/legality failures. **Done.**
5. Build the player-facing web game and complete a human-vs-AI battle. **Done.**
6. Add terrain editing, deployment polish and accessibility improvements.
7. Tune AI behavior before adding 40k.

## Risks

- **Free data coverage:** current-edition core rules are free, but faction
  datasheets and mission packs are not all free. Start with starter-box data and
  user-supplied/community data, and keep the data-pack boundary strict.
- **Manual board editing:** deployment is action-driven, but terrain and
  fine-grained unit placement still need an editor. Test those controls with
  real games early.
- **Rules ambiguity/updates:** AoS 4th has rolling updates and 40k 11th is new.
  Version data packs and record which rules update each game used.
- **AI quality:** legal actions are easy; a plausible opponent takes iteration.
  Use AI-vs-AI batches as a regression harness, but validate the experience with
  human playtests.
- **Roster scope:** a full BattleScribe replacement is a separate project. Keep
  the builder curated.
- **Copyright:** keep PDFs, verbatim rules text and proprietary datasets out of
  the repository.
