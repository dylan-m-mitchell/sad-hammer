import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import json
from api_server import app


def test_session_create_and_ai_turn(tmp_path):
    client = app.test_client()
    # Create session with a tiny AI roster
    resp = client.post('/api/session', json={'units': [{'name': 'AI1', 'aggression': 'Aggressive'}]})
    assert resp.status_code == 200
    data = resp.get_json()
    sid = data['session_id']

    # Run one AI turn — server returns plain text summary
    resp2 = client.post(f'/api/session/{sid}/ai_turn')
    assert resp2.status_code == 200
    # Should be plain text
    text = resp2.get_data(as_text=True)
    assert isinstance(text, str)
    assert 'AI' in text or 'action' in text.lower() or 'No AI actions' in text


def test_notes_endpoint():
    client = app.test_client()
    resp = client.post('/api/session', json={'units': [{'name': 'AI Katz', 'aggression': 'Neutral'}]})
    sid = resp.get_json()['session_id']
    # Post a note
    r = client.post(f'/api/session/{sid}/notes', json={'text': 'Player did X'})
    assert r.status_code == 200
    # Get notes
    g = client.get(f'/api/session/{sid}/notes')
    assert g.status_code == 200
    assert g.get_json().get('notes') and g.get_json()['notes'][0]['text'] == 'Player did X'
