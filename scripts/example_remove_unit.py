#!/usr/bin/env python3
"""Example: Remove AI units when killed by player

This example demonstrates how to:
1. Create a game session with AI units
2. Run AI turns
3. Remove units that have been killed by the player
4. Continue playing with remaining units
"""

import requests
import json

BASE_URL = "http://localhost:5000"


def main():
    print("=== Sad Hammer: Remove Unit Example ===\n")
    
    # 1. Create a session with AI units
    print("1. Creating session with 3 AI units...")
    units = [
        {'name': 'Mournfang Pack A', 'aggression': 'Aggressive'},
        {'name': 'Huskard on Stonehorn', 'aggression': 'Aggressive'},
        {'name': 'Icebrow Hunter', 'aggression': 'Neutral'}
    ]
    
    response = requests.post(
        f"{BASE_URL}/api/session",
        json={'units': units, 'roll_mode': 'ai'}
    )
    
    if response.status_code != 200:
        print(f"Error creating session: {response.text}")
        return
    
    session_data = response.json()
    session_id = session_data['session_id']
    print(f"✓ Session created: {session_id}")
    print(f"  AI units: {session_data['state']['ai_count']}\n")
    
    # 2. Run first AI turn
    print("2. Running first AI turn...")
    response = requests.post(f"{BASE_URL}/api/session/{session_id}/ai_turn")
    
    if response.status_code == 200:
        print("✓ AI Turn 1 completed")
        print(response.text)
    
    # 3. Check session state
    print("\n3. Checking session state...")
    response = requests.get(f"{BASE_URL}/api/session/{session_id}")
    state = response.json()
    print(f"✓ Current turn: {state['turn']}")
    print(f"  Active AI units: {len(state['ai_units'])}")
    for unit in state['ai_units']:
        print(f"    - {unit['name']} ({unit['aggression']})")
    
    # 4. Simulate player killing a unit
    print("\n4. Player kills 'Huskard on Stonehorn'...")
    response = requests.post(
        f"{BASE_URL}/api/session/{session_id}/remove_unit",
        json={'unit_name': 'Huskard on Stonehorn'}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Unit removed: {result['removed_unit']}")
        print(f"  Remaining units: {result['remaining_count']}")
        for unit in result['remaining_units']:
            print(f"    - {unit['name']}")
    else:
        print(f"✗ Error: {response.json()}")
    
    # 5. Run another AI turn with fewer units
    print("\n5. Running second AI turn (with fewer units)...")
    response = requests.post(f"{BASE_URL}/api/session/{session_id}/ai_turn")
    
    if response.status_code == 200:
        print("✓ AI Turn 2 completed")
        print(response.text)
    
    # 6. View the log showing unit removal
    print("\n6. Checking event log...")
    response = requests.get(f"{BASE_URL}/api/session/{session_id}")
    state = response.json()
    
    # Find unit removal events
    removal_events = [e for e in state['log'] if e.get('event') == 'unit_removed']
    if removal_events:
        print(f"✓ Unit removal events found: {len(removal_events)}")
        for event in removal_events:
            print(f"  - Turn {event['turn']}: {event['unit_name']} ({event['reason']})")
    
    # 7. Simulate removing another unit
    print("\n7. Player kills 'Mournfang Pack A'...")
    response = requests.post(
        f"{BASE_URL}/api/session/{session_id}/remove_unit",
        json={'unit_name': 'Mournfang Pack A'}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Unit removed: {result['removed_unit']}")
        print(f"  Remaining units: {result['remaining_count']}")
        for unit in result['remaining_units']:
            print(f"    - {unit['name']}")
    
    # 8. Final AI turn with only one unit
    print("\n8. Running third AI turn (single unit remaining)...")
    response = requests.post(f"{BASE_URL}/api/session/{session_id}/ai_turn")
    
    if response.status_code == 200:
        print("✓ AI Turn 3 completed")
        print(response.text)
    
    print("\n=== Example Complete ===")
    print(f"\nSession ID: {session_id}")
    print("The session is still active and can be queried via the API.")


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running: python api_server.py")
    except Exception as e:
        print(f"Error: {e}")
