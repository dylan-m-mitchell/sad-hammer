# Sad Hammer User Guide

A comprehensive guide to using Sad Hammer for solo Age of Sigmar gaming.

## Overview

Sad Hammer is a card-driven AI system that creates a solo enemy for your Age of Sigmar games. The AI uses battle tactic cards and action cards to determine its behavior each turn, simulating an intelligent opponent.

## Core Concepts

### Aggression Levels

Each AI unit has an aggression level that determines HOW it executes its action cards:

- **Aggressive**: Takes risks - attempts longer charges (12"), prefers running over moving, targets high-threat enemies, only retreats when severely damaged (below 25% strength)
- **Neutral**: Balanced approach - moderate charge ranges (9"), equal mix of running/moving, balanced target selection, retreats at moderate damage (below 40% strength)
- **Cautious**: Plays safe - only charges when close (6"), prefers normal moves over running, targets low-risk enemies, retreats earlier (below 60% strength)

All units participate every turn (just like a real player). Aggression affects tactical decision-making, not whether units act.

### Battle Tactics

Battle tactics define the AI's overall strategy for a turn. Eight tactics are available, entering the deck at different game turns:

**Early Game (Turn 1 - 4 tactics available):**

- **Monstrous Takeover**: Focus on monster units to capture objectives
- **Ferocious Advance**: Move the fastest hero and support it
- **Aggressive Expansion**: Push multiple units toward objectives
- **Conquer**: Secure objectives with battleline troops

**Mid Game (Turn 2 - 1 tactic added):**

- **Broken Ranks**: Break through enemy formations

**Late Game (Turn 3 - 3 tactics added):**

- **Bring It Down**: Eliminate specific high-value targets
- **Slay the Warlord**: Focus on killing the enemy leader
- **Savage Spearhead**: Concentrate forces on a flank

### Action Cards

Each battle tactic has 8 unique action cards plus 4 shared objective cards. These specify:

- **Initiative**: When the unit acts (8 = first, 1 = last)
- **Behavior**: What the unit does (move, charge, attack, etc.)
- **Target**: What the unit focuses on

Units are assigned actions based on the drawn battle tactic and sorted by initiative for execution order.

## Getting Started

### 1. Install the Application

**Option A: Docker (Easiest)**

```bash
docker compose up --build
# Access at http://localhost:8080
```

**Option B: Local Development**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/start_backend.sh  # Terminal 1
./scripts/start_frontend.sh  # Terminal 2
```

### 2. Upload Your Army Roster

1. Export your army from BattleScribe as HTML
2. Click "Upload Roster" in the app
3. Select the exported HTML file
4. Optional: Choose a specific battleplan or leave as Random
5. Click "Create Session"

The uploaded roster becomes the AI's army to control.

### 3. Understand the Interface

- **Event Log**: Shows all AI decisions and outcomes
- **Units List**: Your current army
- **Controls**: Buttons to run AI turns and manage the game

## Running Your First Game

### Turn Flow

Each turn follows this sequence:

1. **Draw Battle Tactic**: AI randomly draws one tactic from available deck
2. **Check Aggression Levels**: Each AI unit's aggression level is logged for reference
3. **Assign Actions**: All units get action cards based on the battle tactic
4. **Execute in Initiative Order**: Actions happen from highest (8) to lowest (1), with aggression modifiers affecting execution
5. **Advance Turn**: Click "Next Turn" to move to player's turn

### Understanding the Event Log

The log shows structured events:

```
=== AI Turn 1 ===
Battle Tactic: Ferocious Advance
Aggression Level: Ironjaw Warboss (AGGRESSIVE)
  - Charge range threshold: 12"
  - Run preference: 70%
  - Retreat threshold: 25%
Action: WAAAGH! Forward! (Initiative 8)
  Behavior: Move toward nearest enemy, then charge if in range
```

**Aggression Level Info:**

- Shows each unit's aggression level and tactical modifiers
- All units receive action cards and participate each turn
- Modifiers affect how the action card is executed (not whether the unit acts)

**Action Cards:**

- Show the card title and initiative
- Describe what the unit should do
- May include specific targets or conditions

## Gameplay Strategies

### Working with Aggression Levels

Assign aggression levels based on unit role and playstyle:

- **Aggressive**: Units that should take risks and pressure the enemy (monsters, heroes, shock troops)
- **Neutral**: Balanced units with flexible tactical roles (battleline infantry, generalists)
- **Cautious**: Units that should play defensively and avoid risky engagements (artillery, support characters, objective holders)

Example setup for an Orruk army:

- Boss on Maw-krusha: AGGRESSIVE (takes risks, long charges, aggressive targets)
- Megaboss: AGGRESSIVE (pushes forward, targets threats)
- Brutes: NEUTRAL (balanced approach, moderate charges)
- Ardboyz: NEUTRAL (hold objectives, balanced tactics)
- Warchanter: CAUTIOUS (defensive positioning, short charges, safe targets)

### Interpreting Battle Tactics

Different tactics push different playstyles:

**Monstrous Takeover** (Turn 1):

- Focuses your monster units
- Use aggressively - monsters are powerful
- Usually heads for center objectives

**Ferocious Advance** (Turn 1):

- Your fastest hero leads
- Supporting units follow
- Creates a powerful spearhead

**Broken Ranks** (Turn 2):

- Very flexible tactic
- Can target either aggressive offense or smart repositioning
- Adapts to battlefield situation

**Savage Spearhead** (Turn 3):

- Concentrates 3 fastest units on one flank
- Can overwhelm player's flank
- High damage potential

## Advanced Usage

### Stateless Session Management

The application uses a stateless API. The client (you) maintains:

- **Seed**: Random number seed for deterministic AI behavior
- **Turn**: Current game turn
- **AI Units**: List of AI units with aggression levels

These are stored in your browser session automatically.

### Manual Unit Management

Use the "Remove Unit" feature when:

- A unit is destroyed in combat
- You want to simulate units leaving the field
- Testing specific scenarios

### Multiple Battles

You can run multiple AI turns in sequence:

1. Advance the turn counter
2. Run another AI turn
3. Review the event log for AI intentions
4. Respond on your actual tabletop game

## Troubleshooting

### AI Not Acting

If units aren't acting:

- Check their aggression levels
- Lower "Neutral" to "Aggressive" for more activity
- Some units are meant to hold (CAUTIOUS)

### Wrong Tactics Available

Battle tactics enter on specific turns:

- T1: 4 tactics (early game options)
- T2: +1 tactic (Broken Ranks)
- T3: +3 tactics (late game aggression)

If you're on Turn 2, only 5 tactics are available, not all 8.

### Understanding Event Order

Actions execute by initiative:

- Initiative 8 happens first
- Initiative 1 happens last
- Same initiative? Resolve simultaneously

This matters when multiple units act in the same phase.

## Tips for Maximum Enjoyment

1. **Start Small**: Begin with 1000-1500 point armies to learn the system
2. **Read the Log**: The event log explains what the AI wants to do - use it!
3. **Experiment**: Try different aggression levels to find your preferred challenge
4. **Replay Games**: Same seed = same AI behavior, perfect for testing tactics

## Reference

- [Quick Start Guide](./quick-start.md) - 5-minute setup
- [API Documentation](./api.md) - Technical API reference
- [Architecture](./architecture.md) - System design details
- [Battle Tactics Reference](./quick-start.md#battle-tactic-card-reference) - All 8 tactics

## External Resources

The battle tactic deck and timing rules are based on the [Woehammer Solo Wargaming series](https://woehammer.com/2021/10/13/solo-wargaming-in-age-of-sigmar/):

- [Solo Wargaming in Age of Sigmar (Part 1)](https://woehammer.com/2021/10/13/solo-wargaming-in-age-of-sigmar/)
- [Solo Wargaming Part 2](https://woehammer.com/2021/10/19/solo-wargaming-part-2/)
- [Solo Wargaming Part 4](https://woehammer.com/2021/11/04/solo-wargaming-in-the-age-of-sigmar-part-4/)
- [Solo Wargaming Part 4.2](https://woehammer.com/2021/11/08/solo-wargaming-in-the-age-of-sigmar-part-4-2/)
- [First Solo Game Report](https://woehammer.com/2021/11/18/my-first-solo-game-of-aos/)
- [Second Solo Game Report](https://woehammer.com/2021/11/24/my-second-solo-game-of-aos/)

## Getting Help

- Check the event log for specific AI behavior explanations
- Review the battle tactic descriptions to understand AI objectives
- Read action card behaviors for exact unit instructions
- The system is deterministic with seeds - replay for understanding
