# Rules references

This page records the official, free rules sources used to design the engine.
It is an index for implementation and testing, not a replacement for the
rulebooks. Do not commit the PDFs, verbatim rules text or proprietary faction
data to this repository.

## Current editions (October 2026)

| System | Edition | Official core rules | Notes |
| --- | --- | --- | --- |
| Warhammer 40,000 | 11th | [Core Rules PDF](https://assets.warhammer-community.com/eng_01-06_warhammer40k_new40k_core_rules-was6fbu1ix-hfewhmxyiy.pdf) | 32.2 MB, last modified 2026-06-01. 11th edition launched 2026-06-20 with the Armageddon box. |
| Warhammer Age of Sigmar | 4th | [Core Rules PDF](https://assets.warhammer-community.com/eng_aos_core&key_the-rules_apr25-t7q3fbv0zb-bit50crc5k.pdf) | 44.9 MB, last modified 2025-03-31. Layer later 2025/2026 rules updates and battlescrolls on top. |

Official downloads pages:

- 40k: <https://www.warhammer-community.com/en-gb/downloads/warhammer-40000/>
- AoS: <https://www.warhammer-community.com/en-gb/downloads/warhammer-age-of-sigmar/>

The PDFs were downloaded on 2026-10-24 to a private reference directory outside
the repository and converted to text for rule mapping. The extracted text is
also not committed.

## Phase structure recorded from the core rules

These are short factual summaries used to structure the modules. The rules
modules and tests must cite the relevant rule section, not copy its text.

### Age of Sigmar 4th

A battle is a fixed number of battle rounds. Each battle round has two turns,
one per player. Each turn has seven steps:

1. Start of Turn
2. Hero Phase
3. Movement Phase
4. Shooting Phase
5. Charge Phase
6. Combat Phase
7. End of Turn

The active player uses abilities first in a phase, then the opponent may use
abilities with the appropriate enemy/any timing. Fight abilities use an
alternating sequence during the Combat Phase. Deployment occurs before the
first battle round. Battle-round priority, underdog status, objectives,
territories and mission scoring are part of the battleplan/mission layer.

Core movement abilities include **Normal Move**, **Run** and **Retreat**. Core
shooting is **Shoot**. Core charge is **Charge** (2D6 charge roll). Core combat
is **Fight**. These are the first abilities to implement in the AoS slice.

### Warhammer 40,000 11th

A battle is a series of battle rounds. Each battle round has:

1. Start of Battle Round
2. Player Turns — each player takes one turn
3. End of Battle Round

Each player turn has seven parts:

1. Start of Turn
2. Command Phase
3. Movement Phase
4. Shooting Phase
5. Charge Phase
6. Fight Phase
7. End of Turn

The Command Phase includes gaining Core CP, battle-shock and command abilities.
The Fight Phase alternates eligible units, starting with the active player, and
units that can fight must do so. Mission rules resolve at the end of the battle
round and/or the end of a turn as specified by the mission.

## First-slice scope

The first playable version of each system targets **core rules plus one
mission**. It does not attempt tournament completeness.

### AoS 4th slice

- One battleplan with a fixed board size, deployment territories and objective
  placement.
- Curated starter forces from the **Skaventide** box:
  - Stormcast Eternals
  - Skaven
- Core phase sequence and the universal Core abilities needed to play:
  move, run, retreat, shoot, charge and fight.
- Attack resolution, saves, ward rolls, damage and objective control.
- The mission's end-of-turn objective scoring.
- Basic terrain keywords: cover and line of sight.

There is no AoS 4th battle-shock step. Bravery is stored for future morale work
but does not affect the current slice. Deferred: priority rolls, full battle
tactics, every faction rule, summoning, advanced terrain, difficult-ground
movement penalties, all manifestations/spells and the full matched-play
battlepack. See [the AoS 4th slice](aos4-slice.md) for the exact implementation
matrix and simplifications.

### 40k 11th slice

- One mission with a fixed board size, deployment map and objective placement.
- Curated starter forces from the **Armageddon** box:
  - Space Marines
  - Orks
- Command CP, battle-shock, movement, shooting, charge and fight.
- Core attack sequence, cover, visibility, objective control and mission VP.
- A small, explicitly supported stratagem subset.

Deferred: full detachment rules, every stratagem, full mission deck, full
terrain rules, army-wide faction mechanics.

## Starter forces

Use a curated subset at roughly 1,000 points rather than every model in the
launch boxes.

- **Skaventide:** 24 Stormcast Eternals and 50 Skaven, each side around 1,200
  points in the box. The first data packs are curated 900-point Stormcast and
  920-point Skaven subsets.
- **Armageddon:** 23 Space Marines and 38 Orks. The first data pack should cover
  a legal, playable subset.

Data-pack entries should record the source and edition/update date. Free core
rules do not grant rights to redistribute all faction datasheets. Users may
supply their own data; the repository should ship only data we are permitted to
include.

## Roster format

BattleScribe is no longer available as an actively maintained app. New Recruit
is the community-standard replacement and reads/exports BattleScribe-compatible
`.ros` and `.rosz` files. The roster path is:

1. Import `.ros`/`.rosz`.
2. Map entries to data-pack unit ids.
3. Report unmatched units, wargear and rules clearly.
4. Offer a curated in-app builder for supported factions.
5. Export `.ros` for interoperability.

The legacy BattleScribe HTML parser can remain as a fallback, not the primary
format.

## Copyright and source policy

- Keep PDFs and extracted rule text outside the repository.
- Do not reproduce large rules passages or proprietary points/datasheet dumps
  without permission.
- Store links, our own summaries, rule ids and structured data needed for
  interoperability.
- Record data-pack provenance and update dates.
- Accept user-supplied rosters/data without redistributing them.
- Review the project license and GW/IP policy before a public release.
