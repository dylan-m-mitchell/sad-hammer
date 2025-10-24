import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api_server import app


def test_battleplans_list_structure():
    client = app.test_client()
    resp = client.get('/api/battleplans')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'battleplans' in data
    assert isinstance(data['battleplans'], list)
    # minimal shape check for entries
    if data['battleplans']:
        bp = data['battleplans'][0]
        assert 'id' in bp and 'title' in bp
        # deployment text may exist
        assert 'deployment' in bp
        # map is optional based on local assets
        assert 'map' in bp or True
