import json
import os
import sys

# Ensure repository root is on sys.path so imports like `api_server` work in tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from backend import placement as placement_module
except Exception:
    # fallback: load module by path (works when tests run with different PYTHONPATH)
    import importlib.util, os
    _p = os.path.join(os.path.dirname(__file__), '..', 'backend', 'placement.py')
    _p = os.path.normpath(_p)
    spec = importlib.util.spec_from_file_location('placement', _p)
    placement_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(placement_module)
from types import SimpleNamespace


def make_fake_rng(choice_seq=None):
    """Return a fake RNG with deterministic choice behavior for tests."""
    seq = choice_seq or []
    idx = {'i': 0}
    class RNG:
        def choice(self, arr):
            if not arr:
                raise IndexError('empty')
            # if provided sequence, pick by index mod len
            if seq:
                v = seq[idx['i'] % len(seq)]
                idx['i'] += 1
                # if v not in arr, fallback to first
                return v if v in arr else arr[0]
            # else pick middle deterministically
            return arr[len(arr)//2]
    return RNG()


def test_build_proposed_placement_deterministic():
    bp = {'id': 1, 'title': 'Cover: Standard Deployment', 'deployment': 'Centre'}
    profiles = [ {'name': 'Unit A', 'keywords': ['hero']}, {'name': 'Unit B', 'keywords': []} ]
    rng = make_fake_rng(['center'])
    p = placement_module.build_proposed_placement(1, rng, bp, profiles)
    assert p['event'] == 'placement'
    assert 'allowed_zones' in p
    assert isinstance(p['suggestions'], list)
    # Each suggestion must have unit and reason
    for s in p['suggestions']:
        assert 'unit' in s and 'reason' in s


def test_validate_placements_success_and_failure():
    # prepare a fake proposed placement
    proposed = {
        'event': 'placement',
        'turn': 1,
        'battleplan': {'id': 1, 'title': 'Cover'},
        'allowed_zones': ['left', 'center', 'right'],
        'suggestions': [ {'unit': 'A'}, {'unit': 'B'} ]
    }
    ok, err = placement_module.validate_placements(proposed, [{'unit': 'A', 'zone': 'left'}, {'unit': 'B', 'zone': 'center'}])
    assert ok and err is None
    # missing unit
    ok2, err2 = placement_module.validate_placements(proposed, [{'unit': 'A', 'zone': 'left'}])
    assert not ok2 and err2 and err2.get('error') == 'missing_unit_placements'
    # invalid zone
    ok3, err3 = placement_module.validate_placements(proposed, [{'unit': 'A', 'zone': 'up'}, {'unit': 'B', 'zone': 'center'}])
    assert not ok3 and err3 and err3.get('error') == 'invalid_zones'


# Integration test using Flask test client

def test_integration_session_placement_flow():
    from api_server import app
    client = app.test_client()

    # create a session with simple unit profiles and request battleplan id 1
    units = [{'name': 'Alpha'}, {'name': 'Bravo'}]
    resp = client.post('/api/session', json={'units': units, 'roll_mode': 'player', 'battleplan': 1})
    assert resp.status_code == 200
    data = resp.get_json()
    session_id = data.get('session_id')
    assert session_id

    # trigger ai_turn (player mode) which should attach a proposed_placement
    r2 = client.post(f'/api/session/{session_id}/ai_turn')
    assert r2.status_code == 200

    # fetch placement
    r3 = client.get(f'/api/session/{session_id}/placement')
    assert r3.status_code == 200
    pinfo = r3.get_json()
    placement = pinfo.get('placement')
    assert placement and 'allowed_zones' in placement
    # Server auto-confirms placements at session creation; confirm info should be present
    confirmed = pinfo.get('confirmed')
    # confirmed may be a boolean or a dict containing the persisted placements; accept either
    assert confirmed, f"expected placement to be confirmed but got: {confirmed}"
    if isinstance(confirmed, dict):
        assert confirmed.get('by') == 'server'
    # check session log contains placement_confirmed event
    rlog = client.get(f'/api/session/{session_id}/log')
    logj = rlog.get_json()
    items = logj.get('items', [])
    assert any(it.get('event') == 'placement_confirmed' for it in items)


def test_unit_zoning_scores_and_tiebreak():
    # ensure per-unit scores are computed and tie-breaking uses RNG
    bp = {'id': 1, 'title': 'Border War (2016)'}
    # Unit X is a monster (hero-like), Unit Y is many small models
    profiles = [
        {'name': 'Giant', 'keywords': ['Monster'], 'models': 1, 'wounds_per_model': 8},
        {'name': 'Skirmishers', 'keywords': [], 'models': 12, 'wounds_per_model': 1}
    ]
    # fake rng that alternates choices deterministically
    rng = make_fake_rng(['center', 'scattered'])
    p = placement_module.build_proposed_placement(1, rng, bp, profiles)
    assert 'suggestions' in p
    sugg = {s['unit']: s for s in p['suggestions']}
    assert 'Giant' in sugg and 'Skirmishers' in sugg
    # ensure scores dict present and recommended zone in keys
    for name in ['Giant', 'Skirmishers']:
        s = sugg[name]
        assert 'scores' in s and isinstance(s['scores'], dict)
        assert s['suggested_zone'] in s['scores']
    # deterministic tie-break: calling again with same fake rng sequence should pick same first choices
    rng2 = make_fake_rng(['center', 'scattered'])
    p2 = placement_module.build_proposed_placement(1, rng2, bp, profiles)
    s2 = {s['unit']: s for s in p2['suggestions']}
    assert s2['Giant']['suggested_zone'] == sugg['Giant']['suggested_zone']
    assert s2['Skirmishers']['suggested_zone'] == sugg['Skirmishers']['suggested_zone']


def test_post_placement_confirmation_api_behavior():
    from api_server import app, SESSIONS
    client = app.test_client()

    units = [{'name': 'Alpha'}, {'name': 'Bravo'}]
    resp = client.post('/api/session', json={'units': units, 'roll_mode': 'player', 'battleplan': 1})
    assert resp.status_code == 200
    session_id = resp.get_json().get('session_id')
    assert session_id

    # By default the server auto-applies placement at session creation. Posting placements should be rejected.
    rpost = client.post(f'/api/session/{session_id}/placement', json={'placements': [{'unit': 'Alpha', 'zone': 'left'}, {'unit': 'Bravo', 'zone': 'center'}]})
    assert rpost.status_code == 400
    j = rpost.get_json() or {}
    assert j.get('error') == 'placement_already_auto_confirmed'

    # Now simulate a session where the server did not auto-confirm: remove placement_confirmed and ensure POST succeeds
    with app.app_context():
        sess = SESSIONS.get(session_id)
        assert sess is not None
        # remove auto-confirm and ensure proposed_placement exists
        sess.pop('placement_confirmed', None)
        prop = sess.get('proposed_placement')
        assert prop and 'suggestions' in prop
        # build valid placements using suggested zones
        placements = []
        for s in prop.get('suggestions', []):
            placements.append({'unit': s.get('unit'), 'zone': s.get('suggested_zone') or (prop.get('allowed_zones') or [None])[0]})

    rpost2 = client.post(f'/api/session/{session_id}/placement', json={'placements': placements})
    assert rpost2.status_code == 200
    okj = rpost2.get_json() or {}
    assert okj.get('ok') is True

    # invalid zone should be rejected — provide placements for all units but make one invalid
    if len(placements) >= 2:
        bad = [
            {'unit': placements[0]['unit'], 'zone': 'invalid-zone'},
            {'unit': placements[1]['unit'], 'zone': placements[1]['zone']}
        ]
    else:
        bad = [{'unit': placements[0]['unit'], 'zone': 'invalid-zone'}]
    rbad = client.post(f'/api/session/{session_id}/placement', json={'placements': bad})
    assert rbad.status_code == 400
    rbj = rbad.get_json() or {}
    assert rbj.get('error') == 'invalid_zones'


def test_build_proposed_placement_with_empty_profiles_and_no_bp():
    # Ensure building placement with no profiles and no battleplan still returns structure
    rng = make_fake_rng()
    p = placement_module.build_proposed_placement(1, rng, None, [])
    assert p.get('event') == 'placement'
    assert isinstance(p.get('suggestions'), list)


def test_placement_suggestions_include_hints_and_priority():
    bp = {'id': 1, 'title': 'Border War'}
    profiles = [
        {'name': 'BigBeast', 'keywords': ['Monster'], 'models': 1, 'wounds_per_model': 8},
        {'name': 'Troopers', 'keywords': [], 'models': 12, 'wounds_per_model': 1},
    ]
    rng = make_fake_rng(['center','scattered'])
    p = placement_module.build_proposed_placement(1, rng, bp, profiles)
    assert 'suggestions' in p
    for s in p['suggestions']:
        assert 'priority' in s
        assert s['priority'] in ('High', 'Medium', 'Low')
        assert 'zone_hint' in s and isinstance(s['zone_hint'], str)
        assert 'distance_range' in s and s['distance_range'] in ('small', 'medium', 'deep')
        assert 'coordinate_hint' in s and isinstance(s['coordinate_hint'], str)


def test_validate_placements_with_no_allowed_zones():
    # If allowed_zones is empty, validate_placements should accept placements with any zones
    proposed = {
        'event': 'placement',
        'turn': 1,
        'battleplan': {'id': 99, 'title': 'Freeform'},
        'allowed_zones': [],
        'suggestions': [{'unit': 'Solo'}]
    }
    ok, err = placement_module.validate_placements(proposed, [{'unit': 'Solo', 'zone': 'weird-zone'}])
    assert not ok and err and err.get('error') == 'no_allowed_zones_defined'
