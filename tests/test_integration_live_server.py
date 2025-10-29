import os
import requests


BASE = os.environ.get("LIVE_BASE", "http://localhost:8080")


def test_session_and_ai_turn_live_server():
    # Create a simple stateless session with two AI units, one Monster and one generic
    sess_payload = {
        "units": [
            {"name": "Mournfang Pack A", "keywords": ["Monster"], "aggression": "Aggressive"},
            {"name": "Huskard on Stonehorn", "keywords": [], "aggression": "Aggressive"},
        ],
        "roll_mode": "ai",
    }

    r = requests.post(f"{BASE}/api/session_stateless", json=sess_payload, timeout=5)
    assert r.status_code == 200, f"session_stateless failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert "seed" in data and "battleplan" in data and "state" in data

    seed = data["seed"]
    state = data["state"]
    ai_units = data.get("ai_units") or state.get("ai_units") or []

    # Request an AI turn; expect valid events in response
    t = data.get("turn", 1)
    r2 = requests.post(
        f"{BASE}/api/ai_turn_stateless",
        json={"seed": seed, "turn": t, "ai_units": ai_units, "roll_mode": "ai"},
        timeout=10,
    )
    assert r2.status_code == 200, f"ai_turn_stateless failed: {r2.status_code} {r2.text[:200]}"
    outcome = r2.json()

    # Verify we received aggression checks and possibly action_resolved events
    events = outcome.get("events") or outcome
    assert events, "No events returned from ai_turn_stateless"

    # Ensure at least one action-related event (action_assigned/action_resolved) is present
    found_action = False
    for ev in events:
        # events can be shaped like {'action_resolved': {...}} or {'aggression_check': True,...}
        if isinstance(ev, dict):
            if "action_resolved" in ev or "action_assigned" in ev:
                found_action = True
                break
            # sometimes action metadata is at top-level
            if any(k in ev for k in ("card_title", "initiative", "behavior", "unit")):
                found_action = True
                break

    assert found_action, f"No action-related events found in AI turn output: {events}"
