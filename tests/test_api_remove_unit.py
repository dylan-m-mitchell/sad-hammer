"""Tests for the API endpoint to remove AI units."""

import pytest
import json
from api_server import app, SESSIONS, SESSIONS_LOCK
from full_simulator import Unit as AIUnit


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
    # Clean up sessions after test
    with SESSIONS_LOCK:
        SESSIONS.clear()


def test_remove_unit_success(client):
    """Successfully remove an AI unit from a session."""
    # Create a session with units
    units_data = [
        {'name': 'Mournfang Pack A', 'aggression': 'Aggressive'},
        {'name': 'Huskard on Stonehorn', 'aggression': 'Aggressive'},
        {'name': 'Icebrow Hunter', 'aggression': 'Neutral'}
    ]
    
    response = client.post('/api/session', 
                          data=json.dumps({'units': units_data}),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    session_id = data['session_id']
    
    # Verify initial state
    response = client.get(f'/api/session/{session_id}')
    assert response.status_code == 200
    state = json.loads(response.data)
    assert len(state['ai_units']) == 3
    
    # Remove one unit
    response = client.post(f'/api/session/{session_id}/remove_unit',
                          data=json.dumps({'unit_name': 'Huskard on Stonehorn'}),
                          content_type='application/json')
    assert response.status_code == 200
    result = json.loads(response.data)
    
    assert result['ok'] is True
    assert result['removed_unit'] == 'Huskard on Stonehorn'
    assert result['remaining_count'] == 2
    assert len(result['remaining_units']) == 2
    
    # Verify the unit is actually removed from the session
    response = client.get(f'/api/session/{session_id}')
    assert response.status_code == 200
    state = json.loads(response.data)
    assert len(state['ai_units']) == 2
    
    unit_names = [u['name'] for u in state['ai_units']]
    assert 'Huskard on Stonehorn' not in unit_names
    assert 'Mournfang Pack A' in unit_names
    assert 'Icebrow Hunter' in unit_names


def test_remove_unit_not_found(client):
    """Return 404 when trying to remove a unit that doesn't exist."""
    # Create a session with units
    units_data = [
        {'name': 'Unit A', 'aggression': 'Aggressive'},
        {'name': 'Unit B', 'aggression': 'Neutral'}
    ]
    
    response = client.post('/api/session', 
                          data=json.dumps({'units': units_data}),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    session_id = data['session_id']
    
    # Try to remove a unit that doesn't exist
    response = client.post(f'/api/session/{session_id}/remove_unit',
                          data=json.dumps({'unit_name': 'Nonexistent Unit'}),
                          content_type='application/json')
    assert response.status_code == 404
    result = json.loads(response.data)
    
    assert 'error' in result
    assert result['error'] == 'unit not found'
    assert result['unit_name'] == 'Nonexistent Unit'


def test_remove_unit_missing_unit_name(client):
    """Return 400 when unit_name is not provided."""
    # Create a session
    units_data = [{'name': 'Unit A', 'aggression': 'Aggressive'}]
    response = client.post('/api/session', 
                          data=json.dumps({'units': units_data}),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    session_id = data['session_id']
    
    # Try to remove without providing unit_name
    response = client.post(f'/api/session/{session_id}/remove_unit',
                          data=json.dumps({}),
                          content_type='application/json')
    assert response.status_code == 400
    result = json.loads(response.data)
    
    assert 'error' in result
    assert result['error'] == 'unit_name required'


def test_remove_unit_session_not_found(client):
    """Return 404 when session doesn't exist."""
    response = client.post('/api/session/nonexistent-session-id/remove_unit',
                          data=json.dumps({'unit_name': 'Unit A'}),
                          content_type='application/json')
    assert response.status_code == 404
    result = json.loads(response.data)
    
    assert 'error' in result
    assert result['error'] == 'session not found'


def test_remove_unit_logs_event(client):
    """Removing a unit should create a log entry."""
    # Create a session with units
    units_data = [
        {'name': 'Unit A', 'aggression': 'Aggressive'},
        {'name': 'Unit B', 'aggression': 'Neutral'}
    ]
    
    response = client.post('/api/session', 
                          data=json.dumps({'units': units_data}),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    session_id = data['session_id']
    
    # Remove a unit
    response = client.post(f'/api/session/{session_id}/remove_unit',
                          data=json.dumps({'unit_name': 'Unit A'}),
                          content_type='application/json')
    assert response.status_code == 200
    
    # Check that the removal was logged
    response = client.get(f'/api/session/{session_id}')
    assert response.status_code == 200
    state = json.loads(response.data)
    
    # Find the removal event in the log
    removal_events = [e for e in state['log'] if e.get('event') == 'unit_removed']
    assert len(removal_events) == 1
    
    event = removal_events[0]
    assert event['unit_name'] == 'Unit A'
    assert event['reason'] == 'killed_by_player'
    assert 'turn' in event


def test_remove_multiple_units_sequentially(client):
    """Should be able to remove multiple units one by one."""
    # Create a session with units
    units_data = [
        {'name': 'Unit A', 'aggression': 'Aggressive'},
        {'name': 'Unit B', 'aggression': 'Neutral'},
        {'name': 'Unit C', 'aggression': 'Cautious'}
    ]
    
    response = client.post('/api/session', 
                          data=json.dumps({'units': units_data}),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    session_id = data['session_id']
    
    # Remove Unit A
    response = client.post(f'/api/session/{session_id}/remove_unit',
                          data=json.dumps({'unit_name': 'Unit A'}),
                          content_type='application/json')
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['remaining_count'] == 2
    
    # Remove Unit C
    response = client.post(f'/api/session/{session_id}/remove_unit',
                          data=json.dumps({'unit_name': 'Unit C'}),
                          content_type='application/json')
    assert response.status_code == 200
    result = json.loads(response.data)
    assert result['remaining_count'] == 1
    
    # Verify only Unit B remains
    response = client.get(f'/api/session/{session_id}')
    assert response.status_code == 200
    state = json.loads(response.data)
    assert len(state['ai_units']) == 1
    assert state['ai_units'][0]['name'] == 'Unit B'


def test_remove_unit_then_run_ai_turn(client):
    """AI turn should work correctly after removing a unit."""
    # Create a session with units
    units_data = [
        {'name': 'Unit A', 'aggression': 'Aggressive'},
        {'name': 'Unit B', 'aggression': 'Aggressive'},
        {'name': 'Unit C', 'aggression': 'Aggressive'}
    ]
    
    response = client.post('/api/session', 
                          data=json.dumps({'units': units_data}),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    session_id = data['session_id']
    
    # Remove Unit B
    response = client.post(f'/api/session/{session_id}/remove_unit',
                          data=json.dumps({'unit_name': 'Unit B'}),
                          content_type='application/json')
    assert response.status_code == 200
    
    # Run an AI turn
    response = client.post(f'/api/session/{session_id}/ai_turn')
    assert response.status_code == 200
    
    # Get the turn events
    response = client.get(f'/api/session/{session_id}/last_turn')
    assert response.status_code == 200
    events = json.loads(response.data)
    
    # Verify Unit B is not in the events
    for event in events.get('events', []):
        if 'unit' in event:
            assert event['unit'] != 'Unit B'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
