#!/usr/bin/env python3
"""Example: Remove AI units (stateless API)

This example demonstrates a stateless flow where the client holds the
initial seed and the current ai_units list. The server does not persist
sessions. Endpoints used:
 - POST /api/session_stateless     -> returns {seed, state, proposed_placement}
 - POST /api/ai_turn_stateless     -> run a single turn deterministically
 - POST /api/remove_unit_stateless -> remove a unit from the provided ai_units

Run this script while the server is running (python api_server.py).
"""

import requests
import json

BASE_URL = "http://localhost:5000"


def main():
    print("=== Sad Hammer: Remove Unit (stateless) Example ===\n")

    # 1. Create an initial stateless session (server returns a seed and initial state)
    print("1. Requesting stateless session with 3 AI units...")
    units = [
        {'name': 'Mournfang Pack A', 'aggression': 'Aggressive'},
        {'name': 'Huskard on Stonehorn', 'aggression': 'Aggressive'},
        {'name': 'Icebrow Hunter', 'aggression': 'Neutral'}
    ]

    response = requests.post(f"{BASE_URL}/api/session_stateless", json={'units': units, 'roll_mode': 'ai'})
    if response.status_code != 200:
        print(f"Error creating stateless session: {response.status_code} {response.text}")
        return

    data = response.json()
    seed = data.get('seed')
    state = data.get('state', {})
    ai_units = state.get('ai_units', units)
    turn = state.get('turn', 1)

    print(f"✓ Seed: {seed}")
    print(f"  Initial turn: {turn}")
    print(f"  AI units: {len(ai_units)}\n")

    # 2. Run first AI turn (stateless)
    print("2. Running first AI turn (stateless)...")
    resp = requests.post(f"{BASE_URL}/api/ai_turn_stateless", json={'seed': seed, 'turn': turn, 'ai_units': ai_units, 'roll_mode': 'ai'})
    if resp.status_code == 200:
        print("✓ AI Turn 1 completed")
        print(resp.text)
    else:
        print(f"AI turn error: {resp.status_code} {resp.text}")

    # 3. Simulate player killing a unit
    print("\n3. Player kills 'Huskard on Stonehorn' (stateless remove)...")
    payload = {'ai_units': ai_units, 'unit_name': 'Huskard on Stonehorn', 'turn': turn}
    r = requests.post(f"{BASE_URL}/api/remove_unit_stateless", json=payload)
    if r.status_code != 200:
        print(f"Error removing unit: {r.status_code} {r.text}")
        return

    res = r.json()
    print(f"✓ Unit removed: {res.get('removed_unit')}")
    remaining = res.get('remaining_units', [])
    print(f"  Remaining units: {len(remaining)}")
    for u in remaining:
        print(f"    - {u.get('name')}")

    # Update client-held ai_units and advance turn
    ai_units = remaining
    turn = turn + 1

    # 4. Run another AI turn with fewer units (stateless)
    print("\n4. Running second AI turn (with fewer units)...")
    resp2 = requests.post(f"{BASE_URL}/api/ai_turn_stateless", json={'seed': seed, 'turn': turn, 'ai_units': ai_units, 'roll_mode': 'ai'})
    if resp2.status_code == 200:
        print("✓ AI Turn 2 completed")
        print(resp2.text)
    else:
        print(f"AI turn error: {resp2.status_code} {resp2.text}")

    print("\n=== Example Complete ===")
    print(f"Seed: {seed}")
    print("Client holds the seed and current ai_units list; server remains stateless.")


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running: python api_server.py")
    except Exception as e:
        print(f"Error: {e}")
