import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api_server import app
import io


def create_player_session_with_paused_turn(client):
    # Create a session with roll_mode=player via JSON and then call ai_turn to create a paused turn
    resp = client.post('/api/session', json={'units': [{'name': 'AI Test', 'aggression': 'Aggressive'}], 'roll_mode': 'player'})
    sid = resp.get_json()['session_id']
    # Call ai_turn to create paused state
    # Call ai_turn; retry a few times if no pending actions are produced (aggression checks are random)
    r = None
    for _ in range(6):
        r = client.post(f'/api/session/{sid}/ai_turn')
        assert r.status_code == 200
        last = client.get(f'/api/session/{sid}/last_turn').get_json()
        events = last.get('events') or []
        rr = next((e for e in events if e.get('event') == 'roll_request'), None)
        if rr and rr.get('pending_actions'):
            break
    assert r is not None
    # ensure paused_turn exists
    g = client.get(f'/api/session/{sid}')
    assert g.status_code == 200
    assert g.get_json().get('roll_mode') == 'player'
    # ensure there is a roll_request pending
    last = client.get(f'/api/session/{sid}/last_turn').get_json()
    events = last.get('events') or []
    rr = next((e for e in events if e.get('event') == 'roll_request'), None)
    assert rr and rr.get('pending_actions'), 'no pending roll_request produced after retries'
    return sid


def test_resolve_rolls_accepts_valid_rolls():
    client = app.test_client()
    sid = create_player_session_with_paused_turn(client)
    # fetch last turn to get request ids
    last = client.get(f'/api/session/{sid}/last_turn').get_json()
    events = last.get('events') or []
    rr = next((e for e in events if e.get('event') == 'roll_request'), None)
    assert rr is not None
    pending = rr.get('pending_actions', [])
    # build payload with valid rolls (1..6)
    payload = {'action_results': []}
    for i, p in enumerate(pending):
        payload['action_results'].append({'request_id': p['request_id'], 'result': {'roll': 4}})
    resp = client.post(f'/api/session/{sid}/resolve_rolls', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('ok') is True
    assert isinstance(data.get('events'), list)


def test_resolve_rolls_rejects_out_of_range():
    client = app.test_client()
    sid = create_player_session_with_paused_turn(client)
    last = client.get(f'/api/session/{sid}/last_turn').get_json()
    rr = next((e for e in (last.get('events') or []) if e.get('event') == 'roll_request'), None)
    pending = rr.get('pending_actions', [])
    # send an out of range roll (7)
    payload = {'action_results': [{'request_id': pending[0]['request_id'], 'result': {'roll': 7}}]}
    resp = client.post(f'/api/session/{sid}/resolve_rolls', json=payload)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get('error') == 'roll_out_of_range'
