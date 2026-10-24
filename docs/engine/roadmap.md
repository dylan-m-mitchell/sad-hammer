# Engine roadmap

This roadmap replaces the earlier “finish the card prototype” plan. The target
is a physical-table companion with a full digital twin, a human-vs-AI loop, and
edition-specific rules for Age of Sigmar 4th and Warhammer 40,000 11th.

## Guiding decisions

- **Interfaces first, one complete slice second.** The shared contracts are
  small and proven by the demo system; the next milestone implements AoS 4th
  fully through those contracts before starting 40k.
- **No universal card engine.** Each edition owns its phases, combat, morale,
  mission scoring and resources. Battle tactics may be mission data, not a
  turn driver.
- **Human authority on the table.** The human rolls their own dice and reports
  the resulting state. The app rolls and resolves for the AI. Validation of
  human updates should warn, not block.
- **Terrain and deployment are part of v1.** Terrain affects line of sight,
  cover, movement and therefore AI decisions. Both editors must work before the
  companion can be tested properly.
- **AI must be legal, explainable and characterful.** Utility scoring over
  system-enumerated actions; aggression profiles change priorities; no machine
  learning in v1.
- **Save/export from day one.** The canonical state is versioned JSON in the
  client. The API stays stateless unless state size forces a cache.
- **Rules content stays out of the repository.** Commit links, summaries and
  structured data, not PDFs or copied rulebook text.

## Current branch

`feature/engine-foundation` contains Phase 0 and the Phase 1 walking skeleton.
No engine work is committed directly to `main`. The legacy card simulator stays
on `main` as reference material until the new AoS slice replaces its UI flow.

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
- [x] Utility AI with aggression profiles, alternatives and explanations.
- [x] CLI demo, save/load and inspect commands.
- [x] Focused engine tests and CI workflow.

**Exit criteria met by the demo:** two armies, a board, terrain, objective,
legal moves and attacks, AI turns, deterministic replay and JSON round-trip.

## Phase 2 — AoS 4th vertical slice

**Goal:** one complete, played-through AoS 4th game with the Skaventide starter
forces, one mission and the core rules.

- [ ] Rules matrix: phases, core abilities, combat sequence, battle-shock,
      terrain, objective control and battle-round scoring.
- [ ] Data packs for a curated Stormcast Eternals force and a curated Skaven
      force from the starter set.
- [ ] Deployment phase: territories, objectives, units, faction terrain and
      validation.
- [ ] Start of Turn, Hero, Movement, Shooting, Charge, Combat and End of Turn.
- [ ] Normal Move, Run, Retreat, Shoot, Charge, Fight and core reactions.
- [ ] Weapon attacks, hit/wound/save/damage, mortal damage, wards and
      destructible units.
- [ ] One mission with battle-round scoring and a battle-round limit.
- [ ] AI v1 using the generic policy and AoS-specific evaluation.
- [ ] Rules tests for every implemented core interaction plus an AI-vs-AI
      regression game.

**Exit:** the AoS game can be played end-to-end through the engine and CLI with a
legal, explainable AI. This is the first real proof that the abstraction works.

## Phase 3 — Physical-table companion UI

**Goal:** play the AoS slice on a real table while keeping the digital twin in
sync.

- [ ] Setup wizard: system, mission, board size, rosters and deployment.
- [ ] Board renderer (SVG or Canvas) with terrain, units and objectives.
- [ ] Editable terrain layout with suggested layouts and overlap/objective
      validation.
- [ ] Editable unit deployment with zone, coherency and footprint checks.
- [ ] AI turn step-through: plan, movement path, target, dice and results.
- [ ] Human turn update wizard at end of turn: positions, casualties, CP/VP,
      objectives and notes.
- [ ] Warnings instead of hard blocks for human-reported state.
- [ ] Local autosave, JSON export/import and replayable event log.
- [ ] Accessibility and mobile/tablet layout.

**Exit:** a full physical-table AoS game is played with the app as the opponent
and digital twin, without entering every human dice roll.

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

**Goal:** the same companion flow for 40k 11th.

- [ ] Rules matrix for 11th edition: battle round, player turns, seven steps,
      Command CP, battle-shock, movement, shooting, charge, fight, end of turn.
- [ ] Curated Armageddon Space Marines and Orks data packs.
- [ ] One mission from the current mission deck.
- [ ] Command-point and stratagem subset; mission scoring.
- [ ] AI policy hooks for CP spending and threat ranges.
- [ ] Shared UI with system-specific controls and phase labels.
- [ ] Cross-system tests proving the core did not become AoS-shaped.

**Exit:** a complete 40k game through the same companion flow with a legal AI.

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

1. Merge the engine foundation and get the focused CI green.
2. Build the AoS 4th rules matrix and the two starter data packs.
3. Implement deployment, movement, shooting, charge, combat and one mission.
4. Play an AI-vs-AI AoS game and fix rules/legality failures.
5. Add the board/deployment UI and the end-of-turn digital-twin wizard.
6. Tune AI behavior before adding 40k.

## Risks

- **Free data coverage:** current-edition core rules are free, but faction
  datasheets and mission packs are not all free. Start with starter-box data and
  user-supplied/community data, and keep the data-pack boundary strict.
- **Manual twin updates:** entering board state is the dominant UX risk. The
  end-of-turn wizard and drag/drop must be tested with real games early.
- **Rules ambiguity/updates:** AoS 4th has rolling updates and 40k 11th is new.
  Version data packs and record which rules update each game used.
- **AI quality:** legal actions are easy; a plausible opponent takes iteration.
  Do not defer AI-vs-AI playtesting until the UI is finished.
- **Roster scope:** a full BattleScribe replacement is a separate project. Keep
  the builder curated.
- **Copyright:** keep PDFs, verbatim rules text and proprietary datasets out of
  the repository.
