# Age of Sigmar 4th vertical slice

This document describes the first playable rules slice: a complete
player-vs-AI Age of Sigmar 4th game using the Skaventide starter forces and one
original mission. The CLI also runs both sides through the AI as a rules and
regression harness. This is the reference for what the engine currently
implements, and for what is deliberately deferred.

The slice is **not** a matched-play ruleset. The data packs are curated,
approximate profiles for the engine and AI. They are not a replacement for the
official datasheets or the current battlepack.

## Play it

```bash
docker compose up --build
# open http://localhost:8080
```

Press Start to play the fixed, server-owned balanced opponent. The web client
supports the full turn loop, automatic AI turns, human picks in alternating
combat, scoring, resume, and versioned export/import. The legacy card simulator
remains at `/legacy`.

The CLI stays available as the AI-vs-AI verification harness:

```bash
# One complete battle round, with command-point spending and scoring.
python -m backend.engine.cli aos4 --seed 7 --rounds 1 --auto-deploy

# A five-round AI-vs-AI regression game, saving the final state.
python -m backend.engine.cli aos4 --seed 11 --rounds 5 \
  --player-profile balanced --ai-profile aggressive \
  --save /tmp/aos4-game.json
```

`--auto-deploy` starts at round 1 with both armies at the mission's default
deployment positions. Without it, deployment uses explicit `deploy` actions and
an `end_deployment` action. The web client offers the same manual deployment
path, but defaults to quick play with both armies deployed.

## Data and mission

| File | Purpose |
| --- | --- |
| `data/aos4/factions/stormcast-starter.json` | Curated Stormcast Eternals starter force, 900 points |
| `data/aos4/factions/skaven-starter.json` | Curated Skaven starter force, 920 points |
| `data/aos4/missions/contested-ground.json` | Original 44x30 mission with five terrain features and four objectives |

The loader validates that packs identify AoS 4th, that unit and weapon ids are
unique, that stats are in range, and that deployment positions and terrain stay
on the board. Mission data supplies the board, deployment zones, objectives,
terrain, scoring and default deployments.

## Rules matrix

| Area | Implemented in the slice | Notes |
| --- | --- | --- |
| Battle round | Two player turns, five-round limit, player always takes the first turn | No priority roll |
| Command points | 4 CP at the start of each battle round, +1 for the underdog, reset at round end | No other CP generation |
| Phases | Start of Turn, Hero, Movement, Shooting, Charge, Combat, End of Turn | Each phase ends through an explicit `end_phase` action |
| Deployment | Mission zones, editable player placement, board/zone/overlap validation | AI units use mission defaults; one placement per unit |
| Start of Turn | Phase transition and turn bookkeeping | No start-of-turn abilities yet |
| Hero | `rally` command restores D3 wounds | No spells, invocations or heroic actions |
| Movement | Normal move, run and retreat | Run adds a D6; retreat suffers D3 mortal damage and prevents shooting/charging |
| Shooting | Ranged weapons, range, line of sight, cover and one attack per unit | Cover imposes -1 to hit; units in combat cannot shoot |
| Charge | 2D6 charge, must finish within 1/2" of the target | Charging units strike first in the following Combat phase |
| Combat | Alternating unit selection, 3" pile-in, melee weapons, one fight per unit | Charged units are resolved before the normal combat pool |
| Attack sequence | Hit, wound, save, damage, ward per damage point | Natural 1s fail; natural 6s hit; critical-mortal weapons skip wound/save |
| Terrain | Polygon cover, line-of-sight blocking, generic features | Difficult-ground data is stored but does not yet reduce movement |
| Objective control | Models x control within an objective's radius; closest objective wins overlapping units | Control is checked at the start of round 1 and at the end of every turn |
| Scoring | Active player scores 1 VP per objective controlled at the end of their turn | `contested-ground` mission rule |
| End of Turn | Score, reset CP at the end of the round, advance the round or finish | Equal scores produce a draw |
| AI | Legal-action utility scoring, fixed balanced opponent, explanations and deterministic tie-breaking; internal profiles for tests | No machine learning |
| Player UI | Responsive board, unit orders, AI intent log, battle log and result flow | Default app route on mobile and web |
| Side ownership | Human and AI can only select actions owned by their side, including combat | Enforced by the play API and engine |
| Save/replay | Versioned JSON save, action log and deterministic replay | Export/import in the UI and CLI save files |

### Combat sequence details

For each attack:

1. Roll to hit. A natural 1 fails, a natural 6 is a critical hit, and other
   results compare against the weapon's hit characteristic after modifiers.
2. If the weapon has the `crit_mortal` keyword, a critical hit adds its damage
   directly to the damage pool without a wound or save roll.
3. Otherwise roll to wound. A natural 1 fails; otherwise compare the roll with
   the weapon's wound characteristic.
4. Roll to save. The target number is `save + rend - save modifiers`, capped at
   2+. A natural 1 always fails.
5. Each point of damage in the pool is then saved separately by the target's
   ward, if it has one. Ward rolls are not modified by rend.

Cover only affects ranged attacks. A unit with the `Fly` keyword ignores cover
and blocking terrain in this slice. A unit that charged this turn does not gain
cover.

### Objective and scoring details

A unit controls an objective when its centre is inside the objective's radius.
If a unit is inside more than one objective, it is assigned to the closest one.
Control is the sum of `models x control` for each side. The side with more
control takes the objective; a tie leaves the previous controller in place.
This means control can persist until an opponent actually takes it.

At the end of a turn, the active player scores the value of every objective
they control. The mission uses 1 VP per objective. The player with the higher
score after the final battle round wins; equal scores are a draw.

## AI behaviour

The AoS module supplies `evaluate_action` and `explain_action` to the generic
policy. Its heuristics value expected damage, objective position, objective
pressure, cover, target health and charge risk. The web game always uses the
fixed `balanced` profile; the CLI and tests can compare the internal profiles,
which change the decision:

- `aggressive` favours damage and accepts more charge risk;
- `balanced` mixes damage, objectives and cover;
- `cautious` favours survival, cover and lower-risk actions.

The policy only selects actions returned by `legal_actions`. Every selected
action is validated again before it is applied. Runs with the same seed and
profile produce the same result, and the event log explains each choice.

The player-facing loop uses the same policy through `run_ai_until_human`. It
filters candidates to AI-owned actions, resolves the AI turn automatically, and
stops when the human's turn begins or alternating combat reaches a human unit.
That keeps control honest in both directions: the AI cannot move or fight with a
player unit, and the player cannot act for the AI.

The AI enumerates a deliberately small set of candidate destinations around
objectives, terrain and enemies. A human-facing client may submit any legal
destination; the candidate set is an AI search limit, not a rules limit.

## Simplifications and deferred work

The following are intentionally outside this slice:

- priority rolls and alternating deployment;
- spells, prayers, manifestations, invocations, battle tactics and
  enhancements;
- faction rules, heroic actions, reactions and the full command list;
- battleshock or other morale tests (AoS 4th does not use battleshock);
- difficult-ground movement penalties and full terrain/visibility rules;
- per-model placement, unit coherency, model counts in weapon ranges and
  casualty removal;
- roster import (`.ros`/`.rosz`) and the curated in-app builder;
- an editable terrain layout and a richer drag-and-drop deployment editor;
- per-action animation, undo, and game replay controls;
- a second mission or a matched-play battlepack.

Bravery is stored in the data packs for future morale work but is not used by
the current rules. The engine also treats each unit as a single centre point
with a base radius; per-model footprints are a later architectural change.

## Tests

The slice is covered by:

- `tests/engine/test_aos4_data.py` - pack and mission validation;
- `tests/engine/test_aos4_combat.py` - attack sequence, wards, probabilities and
  charge odds;
- `tests/engine/test_aos4_system.py` - deployment, phases, movement, shooting,
  charges, combat order, commands, scoring, AI behaviour, save/load and replay;
- `tests/test_api_aos4.py` - the player-facing HTTP loop, full human-vs-AI game
  completion, AI explanations, side ownership, and export/import.

The Engine CI workflow also runs a short `aos4` CLI game as a smoke test.
