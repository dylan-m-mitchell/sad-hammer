# Product

_A quick pick-up-and-play tabletop skirmish against a fair computer opponent:
open, press Start, play._

Sad Hammer is not a toolkit or a tournament platform. The product is one
focused game that a new player can understand and finish without reading a
manual or making setup decisions first.

## Default game

The app opens with a complete battle ready to play:

| Setting | Default |
| --- | --- |
| Forces | Stormcast Eternals vs Skaven starter forces |
| Mission | Contested Ground |
| Length | Five battle rounds |
| Deployment | Both armies already deployed |
| Opponent | Server-owned balanced AI |

Pressing **Start battle** launches that game. There is no required choice of army,
mission, profile, difficulty or seed before the first turn.

**Customize battle** is an optional secondary path for players who want it. It
changes only the mission, the force and the seed. The default game remains one
click away, and opening the customization controls is never required.

## Core loop

1. Open Sad Hammer. The default game is ready.
2. Press Start battle.
3. Play the battle: move, shoot, charge, fight and spend command points while
   the AI takes its own turns.
4. Score objectives at the end of each turn over five battle rounds.
5. Finish the game, resume a saved battle, or export it for later.

The AI explains its important decisions in the battle log so the player can
understand why it acted. The same rules and legal-action contract apply to both
sides.

## Principles

- **No required setup.** Opening the app and pressing Start is enough. Any
  customization is optional and secondary.
- **One server-owned opponent style.** The player never chooses an AI style,
  aggression level or difficulty. The server fixes the opponent to its balanced
  heuristic profile.
- **Explainable AI.** Important AI decisions carry a human-readable reason in
  the UI and the saved log.
- **Save and resume.** Games can be exported as versioned JSON, imported later,
  or resumed from the same browser.
- **No required decision before the first turn.** New features must not add a
  mandatory setup step, dialog or choice between opening the app and playing.

## AI approach

- The opponent is a heuristic utility AI. It scores only the actions the rules
  engine says are legal, using weights for damage, objectives, risk, cover,
  mobility and tempo, then explains its choice.
- The server chooses one fixed `balanced` profile. Profiles are internal tuning
  and testing tools, not player-facing options. The setup response does not
  expose profiles, new games ignore a client-supplied profile, and an imported
  game keeps the profile stored in its save.
- The AI is tuned with a headless AI-vs-AI benchmark:

  ```bash
  python -m backend.engine.cli aos4-bench --games 20
  ```

  This is a development and regression tool, not a product mode.
- The opponent is deliberately beatable. It should be fair, predictable in
  intent, and capable of losing to good play rather than optimized for
  tournament-level tactics.
- There is no LLM, machine-learning or human-gameplay-data dependency. The AI
  is deterministic heuristic code driven by the game seed and the fixed
  profile; the same seed and state replay the same decisions.

## Explicit non-goals

- **List builder.** The product uses curated starter forces. It is not a roster
  construction or list-optimization tool.
- **Accounts.** There is no sign-in, cloud profile or account system. The game
  runs locally for the player.
- **Matchmaking.** The opponent is the server-owned AI. There is no player
  queue, lobby or PvP matchmaking.
- **Player-selected difficulty or aggression.** There is one fixed balanced
  opponent. Difficulty and aggression are not settings.
- **Content buffet.** The product is not a broad library of factions, missions
  and modes. The default game is the product; optional customization stays
  narrow and must not turn into a content browser.
