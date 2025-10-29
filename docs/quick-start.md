# Quick Start Guide

Get up and running with Sad Hammer in 5 minutes.

## Prerequisites

- Python 3.9+
- Docker and Docker Compose (optional, for easier deployment)
- Node.js 18+ (for local frontend development)

## Installation (Choose One)

### Option 1: Docker (Recommended)

This is the fastest way to get started:

```bash
# Clone the repository
git clone <repository-url>
cd sad-hammer

# Start the application
docker compose up --build

# Open your browser to http://localhost:8080
```

The application includes both frontend and backend, ready to use.

### Option 2: Local Development

For developing or customizing the application:

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start backend (in one terminal)
./scripts/start_backend.sh
# Backend runs on http://localhost:5000

# 4. Start frontend (in another terminal)
./scripts/start_frontend.sh
# Frontend runs on http://localhost:5173

# 5. Open browser
# Navigate to http://localhost:5173
```

## Your First Solo Game

### Step 1: Upload a BattleScribe Roster

1. Export your army roster from BattleScribe as HTML
2. Click the **"Upload Roster"** button in the app
3. Select your exported HTML file
4. (Optional) Choose a battleplan or leave as Random
5. Click **"Create Session"**

### Step 2: Understand the Battle Tactic Deck

The AI uses 8 battle tactic cards that enter the deck at different turns:

**Turn 1 (4 cards available):**

- Monstrous Takeover - Prioritize monstrous units to seize objectives
- Ferocious Advance - Aggressive repositioning and charges
- Aggressive Expansion - Move multiple units toward objectives
- Conquer - Focus on taking and holding objectives

**Turn 2:**

- Broken Ranks - Versatile tactic that breaks enemy formations

**Turn 3:**

- Bring It Down - Target a specific enemy unit to be destroyed
- Slay the Warlord - Kill the enemy commander/leader
- Savage Spearhead - Push concentrated force to overwhelm a flank

### Step 3: Run an AI Turn

1. Click **"Run AI Turn"** button
2. The AI will:
   - Draw a battle tactic card
   - Check aggression for each unit (AGGRESSIVE units act, CAUTIOUS units hold)
   - Assign action cards to units that passed aggression checks
   - Execute actions in initiative order
3. Review the event log to see what the AI intends to do

### Step 4: Interpret Results

The event log shows:

- **Aggression Checks**: Which units acted (AGGRESSIVE) vs held (CAUTIOUS/NEUTRAL)
- **Battle Tactic**: What the AI is trying to accomplish this turn
- **Action Cards**: What each acting unit will do
- **Event Details**: Specific instructions for each unit

## Battleplan Selection

When uploading a roster, you can:

- Choose "Random" for unpredictable scenarios
- Select a specific battleplan for a known deployment
- Some battleplans have zone bias maps to suggest AI deployment

## Tips for First Games

1. Start with a small army (1000-1500 points)
2. Use AI mode first to understand the flow
3. Read the event log carefully - it explains the AI's intentions
4. The AI is deterministic with the same seed, so you can replay scenarios
5. Don't forget to advance turns for new battle tactics to enter the deck

## Next Steps

- See [User Guide](./user-guide.md) for detailed workflow
- Read [API Documentation](./api.md) to integrate with your own tools
- Check [Architecture](./architecture.md) to understand the card system

## Battle Tactic Card Reference

The AI uses 8 battle tactic cards that enter the deck at different turns. Each tactic defines what the AI should focus on that turn.

### Turn 1 Cards (Available from Start)

| Card                     | Description                                    | Target Units           | Objectives                                |
| ------------------------ | ---------------------------------------------- | ---------------------- | ----------------------------------------- |
| **Monstrous Takeover**   | Prioritize monstrous units to seize objectives | All Monsters           | Nearest objective to designated monster   |
| **Ferocious Advance**    | Aggressive repositioning and charges           | Hero with highest move | Objective closest to designated hero      |
| **Aggressive Expansion** | Move multiple units toward objectives          | All units within 18"   | All uncontrolled objectives               |
| **Conquer**              | Focus on taking and holding objectives         | All Battleline units   | Two closest objectives to deployment zone |

### Turn 2 Card

| Card             | Description                                   | Target Units | Objectives                            |
| ---------------- | --------------------------------------------- | ------------ | ------------------------------------- |
| **Broken Ranks** | Versatile tactic that breaks enemy formations | All units    | Center or closest to enemy Battleline |

### Turn 3 Cards

| Card                 | Description                                  | Target Units        | Objectives                     |
| -------------------- | -------------------------------------------- | ------------------- | ------------------------------ |
| **Bring It Down**    | Target a specific enemy unit to be destroyed | All units           | Destroy designated enemy unit  |
| **Slay the Warlord** | Kill the enemy commander/leader              | All units           | Eliminate enemy general/leader |
| **Savage Spearhead** | Push concentrated force to overwhelm flank   | Three fastest units | Flank objective on same side   |

## Troubleshooting

**Can't upload roster?**

- Ensure the file is a valid BattleScribe HTML export
- Check browser console for errors

**Server not responding?**

- Verify backend is running on port 5000
- Check firewall settings

**Tests failing?**

- Run `pytest tests/ -v` to see detailed output
- Ensure virtual environment is activated

## Support

For issues or questions:

- Check the [Architecture Documentation](./architecture.md)
- Review test files in `tests/` for usage examples
- Read the source code comments for implementation details
