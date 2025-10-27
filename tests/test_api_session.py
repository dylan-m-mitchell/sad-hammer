import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import json
from api_server import app


def test_session_create_and_ai_turn(tmp_path):
    client = app.test_client()
    # Create stateless session with a tiny AI roster
    resp = client.post('/api/session_stateless', json={'units': [{'name': 'AI1', 'aggression': 'Aggressive'}]})
    assert resp.status_code == 200
    data = resp.get_json() or {}
    seed = data.get('seed')
    state = data.get('state') or {}
    assert seed is not None
    # Run one AI turn in stateless mode
    ai_units = state.get('ai_units') or []
    r2 = client.post('/api/ai_turn_stateless', json={'seed': seed, 'turn': state.get('turn', 1), 'ai_units': ai_units, 'roll_mode': 'ai'})
    assert r2.status_code == 200
    j = r2.get_json() or {}
    assert 'events' in j


def test_notes_endpoint():
    client = app.test_client()
    # Sessionful notes endpoints have been removed in favor of client-side notes.
    # POSTing to /api/session should return 404 (endpoint removed) and notes endpoints should return 404 as well.
    resp = client.post('/api/session', json={'units': [{'name': 'AI Katz', 'aggression': 'Neutral'}]})
    assert resp.status_code == 404
    # Legacy notes endpoints return 404
    r = client.post('/api/session/nonexistent/notes', json={'text': 'Player did X'})
    assert r.status_code == 404
    g = client.get('/api/session/nonexistent/notes')
    assert g.status_code == 404
