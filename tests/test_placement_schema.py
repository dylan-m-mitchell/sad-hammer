import os
import sys
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api_server import app


def test_placement_schema_basic_shape():
    client = app.test_client()
    # create session with a tiny roster
    resp = client.post('/api/session', json={'units': [{'name': 'P1'},{'name': 'P2'}], 'roll_mode': 'ai'})
    assert resp.status_code == 200
    sid = resp.get_json().get('session_id')
    assert sid

    r = client.get(f'/api/session/{sid}/placement')
    assert r.status_code == 200
    j = r.get_json() or {}
    placement = j.get('placement')
    assert placement is not None
    # top-level required keys
    for k in ('event', 'turn', 'allowed_zones', 'suggestions'):
        assert k in placement
    assert placement.get('event') == 'placement'
    assert isinstance(placement.get('turn'), int)
    assert isinstance(placement.get('suggestions'), list)

    # suggestions must contain expected fields
    for s in placement.get('suggestions'):
        assert 'unit' in s
        assert 'scores' in s and isinstance(s['scores'], dict)
        # optional hint fields if present should be the right types
        if 'priority' in s:
            assert s['priority'] in ('High', 'Medium', 'Low')
        if 'distance_range' in s:
            assert s['distance_range'] in ('small', 'medium', 'deep')
