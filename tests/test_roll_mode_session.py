import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import io
from api_server import app


def test_create_session_with_roll_mode_json():
    client = app.test_client()
    resp = client.post('/api/session', json={'units': [{'name': 'AI JSON', 'aggression': 'Neutral'}], 'roll_mode': 'player'})
    assert resp.status_code == 200
    data = resp.get_json()
    sid = data['session_id']
    # fetch session state
    g = client.get(f'/api/session/{sid}')
    assert g.status_code == 200
    assert g.get_json().get('roll_mode') == 'player'


def test_create_session_with_roll_mode_file(tmp_path):
    client = app.test_client()
    # create a tiny temp html file mimicking a Battlescribe export
    html = b"<html><body><roster><unit><name>AI File</name></unit></roster></body></html>"
    data = {
        'file': (io.BytesIO(html), 'roster.html'),
        'roll_mode': 'player'
    }
    resp = client.post('/api/session', content_type='multipart/form-data', data=data)
    assert resp.status_code == 200
    sid = resp.get_json()['session_id']
    g = client.get(f'/api/session/{sid}')
    assert g.status_code == 200
    assert g.get_json().get('roll_mode') == 'player'
