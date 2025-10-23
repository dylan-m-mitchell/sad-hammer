#!/usr/bin/env python3
"""Simple Flask API to serve the Battlescribe parser and simulator to a web frontend.

Endpoints:
- POST /api/load_roster : multipart file upload 'file' -> returns parsed units JSON
- POST /api/run_simulation : JSON payload { "units": [...] , "turns": N, "seed": S } -> returns list of events

This is intended for local development only.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import tempfile
import os

from battlescribe_parser import parse_battlescribe_html
from full_simulator import SoloSimulator, Unit as AIUnit
import uuid
from threading import Lock

app = Flask(__name__)
CORS(app)

# In-memory sessions: session_id -> {'sim': SoloSimulator, 'ai_units': [AIUnit], 'ai_profiles': [...], 'log': []}
SESSIONS = {}
SESSIONS_LOCK = Lock()

# Serve the web frontend (static) from the web/ directory
@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('web', filename)


@app.route('/api/load_roster', methods=['POST'])
def load_roster():
    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    f = request.files['file']
    # save to a temp file and parse
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
        tmp.write(f.read())
        tmp_path = tmp.name

    try:
        units = parse_battlescribe_html(tmp_path)
        return jsonify({'units': units})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.route('/api/run_simulation', methods=['POST'])
def run_simulation_api():
    data = request.get_json(force=True)
    units = data.get('units')
    turns = int(data.get('turns', 5))
    seed = int(data.get('seed', 1))
    # For quick one-off runs we treat provided units as an AI roster and run the SoloSimulator
    ai_units = []
    if units:
        for u in units:
            ai_units.append(AIUnit(u.get('name', 'Unit'), aggression=u.get('aggression', 'Neutral')))
    else:
        # fallback sample AI units
        ai_units = [AIUnit('Mournfang Pack A', aggression='Aggressive'), AIUnit('Huskard on Stonehorn', aggression='Aggressive')]

    events = []
    sim = SoloSimulator(ai_units, seed=seed)
    try:
        for _ in range(turns):
            out = sim.simulate_turn()
            # copy events
            for ev in out:
                events.append(ev.copy())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'events': events})


@app.route('/api/session', methods=['POST'])
def create_session():
    """Create a new session from an uploaded roster file (multipart 'file') or from JSON 'units'.
    Returns: { session_id, state }
    """
    # Accept file upload or JSON body
    units_payload = None
    if request.files and 'file' in request.files:
        f = request.files['file']
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
            tmp.write(f.read())
            tmp_path = tmp.name
        try:
            units_payload = parse_battlescribe_html(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    else:
        data = request.get_json(silent=True) or {}
        units_payload = data.get('units')

    # Previously we treated an uploaded roster as the player's army.
    # Invert that: uploaded rosters become the AI-controlled army. The player's army will be managed via separate endpoints.
    ai_units = []
    ai_profiles = []  # full parsed AI unit profiles (for frontend display)
    if units_payload:
        for u in units_payload:
            # Richer aggression modifier heuristic combining multiple factors.
            # Robust to missing or malformed fields.
            def _int(v, default=0):
                try:
                    return int(v)
                except Exception:
                    return default

            models = _int(u.get('models'))
            wounds = _int(u.get('wounds_per_model'))
            attacks = _int(u.get('attacks'))
            keywords = [k.lower() for k in (u.get('keywords') or []) if isinstance(k, str)]

            # Model-based modifier: +1 per 5 models, -1 for single-model skirmish units
            if models <= 1:
                model_mod = -1
            else:
                model_mod = models // 5

            # Wounds-based modifier: bigger models are tougher; modest weighting
            if wounds >= 6:
                wounds_mod = 2
            elif wounds >= 3:
                wounds_mod = 1
            else:
                wounds_mod = 0

            # Attacks-based modifier: more attacks increases chance to act
            if attacks >= 3:
                attacks_mod = 2
            elif attacks >= 2:
                attacks_mod = 1
            else:
                attacks_mod = 0

            # Keyword bonuses (Hero/Monster are stronger)
            keyword_mod = 0
            if any('monster' in k for k in keywords):
                keyword_mod += 2
            if any('hero' in k for k in keywords):
                keyword_mod += 1

            raw_mod = model_mod + wounds_mod + attacks_mod + keyword_mod
            # Cap modifier so it's sane across many rosters
            mod = max(-2, min(5, raw_mod))

            # create AIUnit skeleton for SoloSimulator with aggression modifier
            ai_units.append(AIUnit(u.get('name', 'Unit'), aggression=u.get('aggression', 'Neutral'), aggression_modifier=mod))
            ai_profiles.append(u)
    else:
        # fallback sample AI units
        ai_units = [AIUnit('Mournfang Pack A', aggression='Aggressive'), AIUnit('Huskard on Stonehorn', aggression='Aggressive')]

    # Create SoloSimulator instance for AI units
    sim = SoloSimulator(ai_units)

    session_id = str(uuid.uuid4())
    with SESSIONS_LOCK:
        SESSIONS[session_id] = {
            'sim': sim,
            'ai_units': ai_units,
            'ai_profiles': ai_profiles,
            'log': []
        }

    return jsonify({'session_id': session_id, 'state': {'turn': sim.turn, 'ai_count': len(ai_units)}})


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session_state(session_id):
    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({'error': 'session not found'}), 404

    sim = sess['sim']
    # return simple state: turn, player units list summary, ai units list summary, log
    ai = [{'name': u.name, 'aggression': getattr(u, 'aggression', None)} for u in sess['ai_units']]
    # include AI parsed profiles (if available) for richer frontend display
    ai_profiles = sess.get('ai_profiles', [])
    return jsonify({'turn': sim.turn, 'ai_units': ai, 'ai_profiles': ai_profiles, 'log': sess['log']})


# Player unit CRUD endpoints removed: server does not model or persist player units.


# Note: player actions are not modeled by this server. The app only runs an AI opponent
# based on uploaded rosters and the card decks.


@app.route('/api/session/<session_id>/ai_turn', methods=['POST'])
def ai_turn(session_id):
    """Run a single AI turn for the session and return the events produced."""
    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({'error': 'session not found'}), 404

    sim = sess['sim']
    # Use SoloSimulator.simulate_turn() to run one AI turn
    events = sim.simulate_turn()
    # Append to session log
    sess['log'].extend(events)
    # store the last turn number and structured events so clients can fetch them
    sess['last_turn'] = sim.turn - 1
    sess['last_turn_events'] = events

    # Build a human-readable summary for players with a clear turn header
    lines = []
    lines.append(f"=== AI Turn {sim.turn - 1} ===")
    for entry in events:
        if 'unit' in entry and 'aggression_check' in entry:
            act = 'ACT' if entry['aggression_check'] else 'HOLD'
            # include roll and modifier debug info when available
            roll = entry.get('roll')
            mod = entry.get('modifier')
            total = entry.get('total')
            target = entry.get('target')
            if roll is not None:
                lines.append(f"AI check: {entry['unit']} -> {act} (d6={roll} + mod={mod} => total={total} vs target={target})")
            else:
                lines.append(f"AI check: {entry['unit']} -> {act}")
        elif 'action_resolved' in entry:
            ar = entry['action_resolved']
            title = ar.get('card_title') or ar.get('card', {}).get('title', '')
            beh = ar.get('behavior', '')
            lines.append(f"AI action: {ar.get('unit')} -> {title} ({ar.get('initiative', '')}) {beh}")
        else:
            # fallback: present the entry as JSON-ish text
            try:
                import json as _json
                lines.append(_json.dumps(entry))
            except Exception:
                lines.append(str(entry))

    # Add a trailing blank line to separate turns clearly
    text = '\n'.join(lines) + '\n\n' if lines else 'No AI actions this turn.\n\n'
    return (text, 200, {'Content-Type': 'text/plain; charset=utf-8'})


@app.route('/api/session/<session_id>/last_turn', methods=['GET'])
def get_last_turn_events(session_id):
    """Return the structured events produced by the last AI turn for this session.

    This is intended for debugging or programmatic consumption (JSON).
    """
    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({'error': 'session not found'}), 404

    return jsonify({'turn': sess.get('last_turn'), 'events': sess.get('last_turn_events', [])})


@app.route('/api/session/<session_id>/log', methods=['GET'])
def get_session_log(session_id):
    """Return the session log with pagination.

    Query params:
      - page (1-based, default 1)
      - size (items per page, default 50)

    Response: { turn, page, size, total, items: [...] }
    """
    # parse query params defensively
    try:
        page = int(request.args.get('page', 1))
    except Exception:
        page = 1
    try:
        size = int(request.args.get('size', 50))
    except Exception:
        size = 50
    if page < 1:
        page = 1
    if size < 1:
        size = 50

    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({'error': 'session not found'}), 404

    log = sess.get('log', [])
    total = len(log)
    start = (page - 1) * size
    end = start + size
    items = log[start:end]

    sim_turn = None
    if 'sim' in sess and getattr(sess.get('sim'), 'turn', None) is not None:
        sim_turn = sess['sim'].turn

    return jsonify({'turn': sim_turn, 'page': page, 'size': size, 'total': total, 'items': items})


@app.route('/api/session/<session_id>/notes', methods=['POST'])
def post_session_note(session_id):
    """Record a free-form player note for the session. JSON: { text: str }"""
    data = request.get_json(force=True) or {}
    text = data.get('text')
    if not text:
        return jsonify({'error': 'text required'}), 400
    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
        if not sess:
            return jsonify({'error': 'session not found'}), 404
        notes = sess.setdefault('notes', [])
        note = {'text': text}
        notes.append(note)
    return jsonify({'ok': True, 'note': note})


@app.route('/api/session/<session_id>/notes', methods=['GET'])
def get_session_notes(session_id):
    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({'error': 'session not found'}), 404
    return jsonify({'notes': sess.get('notes', [])})


if __name__ == '__main__':
    # bind to 0.0.0.0 so the app is reachable from nginx in docker-compose
    app.run(host='0.0.0.0', port=5000, debug=True)
