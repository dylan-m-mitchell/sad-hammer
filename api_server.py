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
from copy import deepcopy
from reference_card_decks import tactic_to_actions, battleplan_deck
from backend import placement as placement_module
import json
import hashlib
import random as _random

app = Flask(__name__)
CORS(app)

# Legacy sessionful endpoints were removed. Add explicit stubs that return 404
# so clients POSTing to old `/api/session` paths receive a clear 404 instead
# of a 405 caused by the generic static-file route below.
@app.route('/api/session', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def legacy_session_root():
    return jsonify({'error': 'session endpoints removed'}), 404


@app.route('/api/session/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def legacy_session_sub(subpath):
    return jsonify({'error': 'session endpoints removed'}), 404

# NOTE: server is now stateless for simulation flows. All sessionful server-side
# state (previously in SESSIONS) has been removed. Clients must provide the
# initial seed, current turn, and AI unit list for stateless endpoints.

# Load optional battleplan -> zone bias mapping (allows controlling which deployment
# zones are permitted/weighted for each battleplan). This file is authored under
# backend/battleplan_zone_bias.json and is used to report allowed zones in the
# placement event emitted on the initial AI turn.
BATTLEPLAN_ZONE_BIAS = []
_bp_bias_path = os.path.join(os.path.dirname(__file__), 'backend', 'battleplan_zone_bias.json')
try:
    with open(_bp_bias_path, 'r', encoding='utf-8') as _f:
        BATTLEPLAN_ZONE_BIAS = json.load(_f)
except Exception:
    # silently ignore missing/invalid file; placement will fall back to freeform text
    BATTLEPLAN_ZONE_BIAS = []


def _get_zone_info_for_bp(bp):
    """Return the zone bias entry for the given battleplan dict or None.

    bp may be a dict from `battleplan_deck` (with 'id' or 'title'). We match
    by id first, then by case-insensitive title.
    """
    if not bp:
        return None
    try:
        bid = bp.get('id')
        if bid is not None:
            for entry in BATTLEPLAN_ZONE_BIAS:
                if entry.get('id') == bid:
                    return entry
    except Exception:
        pass
    try:
        title = str(bp.get('title', '')).lower()
        for entry in BATTLEPLAN_ZONE_BIAS:
            if str(entry.get('title', '')).lower() == title:
                return entry
    except Exception:
        pass
    return None


def _find_map_for_bp(bp):
    """Return a map URL (under /assets/battleplan_maps/) for the given battleplan dict, or None.

    Tries several filename patterns against the `battleplans-media` directory and returns
    the first match. Patterns include: Title-Case hyphenated, slug, raw title, stripped-parentheses,
    and common extensions (.jpg, .jpeg, .png, .webp).
    """
    if not bp:
        return None
    base_dir = os.path.join(os.path.dirname(__file__), 'battleplans-media')
    # collect candidate stems
    stems = []
    try:
        title = str(bp.get('title', '')).strip()
    except Exception:
        title = ''
    if title:
        # Title-Case hyphenated
        parts = [p for p in [w for w in __import__('re').split(r'[^A-Za-z0-9]+', title)] if p]
    # Fallback: build via safe transforms (avoid complex errors)
    try:
        raw = title
        # slug
        slug = raw.lower().replace(' ', '-').replace('/', '-').replace("'", '').replace('"', '')
        slug = __import__('re').sub(r'[^a-z0-9\-]+', '-', slug).strip('-')
        stems.append(slug)
        # title-case hyphen
        words = [w for w in __import__('re').split(r'[^A-Za-z0-9]+', raw) if w]
        if words:
            title_case = '-'.join([w[0].upper() + w[1:] if len(w) > 1 else w.upper() for w in words])
            stems.append(title_case)
            stems.append(title_case + '-2048x1524')
        # raw with spaces
        stems.append(raw)
        stems.append(raw + '-2048x1524')
        # stripped parentheses
        stripped = __import__('re').sub(r'\s*\([^\)]*\)\s*', '', raw).strip()
        if stripped and stripped != raw:
            ws = [w for w in __import__('re').split(r'[^A-Za-z0-9]+', stripped) if w]
            stripped_hy = '-'.join([w[0].upper() + w[1:] if len(w) > 1 else w.upper() for w in ws])
            stems.append(stripped_hy)
            stems.append(stripped_hy + '-2048x1524')
    except Exception:
        stems = stems or []

    # candidate extensions
    exts = ['.jpg', '.jpeg', '.png', '.webp']
    for stem in stems:
        for ext in exts:
            fname = f"{stem}{ext}"
            fpath = os.path.join(base_dir, fname)
            try:
                if os.path.exists(fpath):
                    return f"/assets/battleplan_maps/{fname}"
            except Exception:
                continue
    # No file found
    return None

# Serve the web frontend (static) from the web/ directory
@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('web', filename)


# Serve battleplan map images from the repository `battleplans-media/` directory
@app.route('/assets/battleplan_maps/<path:filename>')
def battleplan_maps(filename):
    # Security: avoid directory traversal by normalizing path
    base = os.path.join(os.path.dirname(__file__), 'battleplans-media')
    return send_from_directory(base, filename)


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



@app.route('/api/battleplans', methods=['GET'])
def list_battleplans():
    # Return the available battleplan cards (id and title and short deployment text)
    plans = []
    for b in battleplan_deck:
        p = {'id': b.get('id'), 'title': b.get('title'), 'deployment': b.get('deployment')}
        try:
            murl = _find_map_for_bp(b)
            if murl:
                p['map'] = murl
        except Exception:
            pass
        plans.append(p)
    return jsonify({'battleplans': plans})


# Player unit CRUD endpoints removed: server does not model or persist player units.


# Note: player actions are not modeled by this server. The app only runs an AI opponent
# based on uploaded rosters and the card decks.





def _derive_seed(initial_seed, turn):
    """Derive a 32-bit integer seed from an initial seed and a turn number.

    This uses SHA-256(initial_seed:turn) and returns the first 32 bits as an int.
    """
    if initial_seed is None:
        # fallback to random seed
        return _random.getrandbits(32)
    s = f"{initial_seed}:{turn}"
    h = hashlib.sha256(s.encode('utf-8')).digest()
    return int.from_bytes(h[:4], 'big')


@app.route('/api/session_stateless', methods=['POST'])
def create_session_stateless():
    """Create a stateless session response. Returns an initial seed and AI unit/profile data.

    Accepts the same payload as POST /api/session (multipart file upload 'file' or JSON 'units'),
    but does NOT persist any server-side session. Returns: { seed, battleplan, state: { turn, ai_units, ai_profiles, roll_mode }, proposed_placement }
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

    ai_units = []
    ai_profiles = []
    if units_payload:
        for u in units_payload:
            ai_units.append(AIUnit(u.get('name', 'Unit'), aggression=u.get('aggression', 'Neutral'), aggression_modifier=u.get('aggression_modifier', 0)))
            ai_profiles.append(u)
    else:
        ai_units = [AIUnit('Mournfang Pack A', aggression='Aggressive'), AIUnit('Huskard on Stonehorn', aggression='Aggressive')]

    # roll_mode and chosen_battleplan same handling as create_session
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    roll_mode = data.get('roll_mode') if data else None
    if roll_mode not in ('ai', 'player'):
        # check form
        roll_mode = request.form.get('roll_mode') if 'roll_mode' in request.form else 'ai'

    chosen_bp = None
    if data and 'battleplan' in data:
        chosen_bp = data.get('battleplan')
    else:
        if 'battleplan' in request.form:
            chosen_bp = request.form.get('battleplan')

    selected_battleplan = None
    try:
        if chosen_bp is not None:
            try:
                cid = int(chosen_bp)
                selected_battleplan = next((b for b in battleplan_deck if b.get('id') == cid), None)
            except Exception:
                selected_battleplan = next((b for b in battleplan_deck if str(b.get('title')).lower() == str(chosen_bp).lower()), None)
        if not selected_battleplan:
            try:
                rng = _random.Random()
                selected_battleplan = rng.choice(battleplan_deck)
            except Exception:
                import random as _rnd
                selected_battleplan = _rnd.choice(battleplan_deck)
    except Exception:
        selected_battleplan = battleplan_deck[0] if battleplan_deck else None

    # Generate an initial seed to return to the client; client will send this seed for subsequent calls
    seed = _random.getrandbits(32)

    # Build a SoloSimulator locally to compute an initial proposed placement (statelessly)
    sim = SoloSimulator(ai_units, seed=seed)
    placement = None
    try:
        if selected_battleplan:
            placement = placement_module.build_proposed_placement(sim.turn, sim.rng, selected_battleplan, ai_profiles)
    except Exception:
        placement = None

    # Return a minimal state object
    state = {'turn': sim.turn, 'ai_units': [{'name': u.name, 'aggression': getattr(u, 'aggression', None)} for u in ai_units], 'ai_profiles': ai_profiles, 'roll_mode': roll_mode}
    bp_info = None
    if selected_battleplan:
        bp_info = {'id': selected_battleplan.get('id'), 'title': selected_battleplan.get('title'), 'deployment': selected_battleplan.get('deployment')}
        try:
            m = _find_map_for_bp(selected_battleplan)
            if m:
                bp_info['map'] = m
        except Exception:
            pass

    return jsonify({'seed': seed, 'battleplan': bp_info, 'state': state, 'proposed_placement': placement})


@app.route('/api/ai_turn_stateless', methods=['POST'])
def ai_turn_stateless():
    """Run a single AI turn deterministically from an initial seed and turn index.

    Expected JSON: { seed: <int|string>, turn: <int>, ai_units: [...], roll_mode: 'ai'|'player', battleplan: <optional> }
    Returns: { turn: <int>, events: [...], pending_actions: [...](if player mode) }
    """
    data = request.get_json(force=True) or {}
    seed = data.get('seed')
    turn = int(data.get('turn', 1))
    roll_mode = data.get('roll_mode', 'ai')
    ai_units_payload = data.get('ai_units') or []
    battleplan = data.get('battleplan')

    # Reconstruct Unit objects
    units = []
    for u in ai_units_payload:
        name = u.get('name') if isinstance(u, dict) else str(u)
        agg = u.get('aggression') if isinstance(u, dict) else None
        agg_mod = u.get('aggression_modifier', 0) if isinstance(u, dict) else 0
        units.append(AIUnit(name, aggression=agg or 'Neutral', aggression_modifier=agg_mod))

    # Derive a per-turn seed and instantiate a SoloSimulator seeded with it
    derived = _derive_seed(seed, turn)
    sim = SoloSimulator(units, seed=derived)
    # Force simulator to the requested turn so internal deck managers consider the correct turn
    sim.turn = turn

    events = []
    pending_actions = []

    if roll_mode == 'player':
        # advance tactic deck and draw tactic
        sim.tactics_deck.advance_turn(sim.turn)
        tactic_card = sim.choose_battle_tactic()
        if tactic_card is None:
            return jsonify({'turn': sim.turn, 'events': [{'event': 'no_tactic_available'}]})

        tactic_title = tactic_card.get('title')

        # aggression checks
        for u in sim.units:
            check = sim.aggression_check(u)
            will_act = check['result']
            events.append({
                'event': 'aggression_check',
                'unit': u.name,
                'aggression_check': will_act,
                'roll': check['roll'],
                'modifier': check['modifier'],
                'total': check['total'],
                'target': check['target'],
            })

        # Use deck_manager to create action assignments
        from deck_manager import create_turn_action_assignments
        action_assignments = create_turn_action_assignments(tactic_card, sim.units, {u.name: True for u in sim.units if True}, rng=sim.rng)

        # Build pending_actions in the same format the frontend expects
        drawn_actions = []
        for idx, assignment in enumerate(action_assignments):
            req_id = f"{sim.turn}-{idx}"
            drawn_actions.append({
                'request_id': req_id,
                'unit': assignment['unit'],
                'card': assignment['card'],
                'initiative': assignment['initiative'],
                'behavior': assignment['behavior'],
                'dice': {'count': 1, 'sides': 6}
            })

        pending_actions = drawn_actions
        events.append({
            'event': 'roll_request',
            'turn': sim.turn,
            'tactic': tactic_title,
            'pending_actions': [
                {
                    'request_id': a['request_id'],
                    'unit': a['unit'],
                    'card_title': a['card'].get('title') if isinstance(a.get('card'), dict) else None,
                    'initiative': a['initiative'],
                    'behavior': a['behavior'],
                    'dice': a.get('dice', {'count': 1, 'sides': 6})
                } for a in drawn_actions
            ]
        })

        return jsonify({'turn': sim.turn, 'events': events, 'pending_actions': pending_actions})

    # default AI mode: run the turn fully
    resolved = sim.simulate_turn()
    # ensure events are JSON-serializable
    return jsonify({'turn': turn, 'events': resolved})


@app.route('/api/resolve_rolls_stateless', methods=['POST'])
def resolve_rolls_stateless():
    """Resolve player-provided roll results for a paused turn in a stateless way.

    Expected JSON: { seed, turn, pending_actions: [...], action_results: [...] }
    Returns: { ok: true, events: [action_resolved, ...] }
    """
    data = request.get_json(force=True) or {}
    seed = data.get('seed')
    turn = int(data.get('turn', 1))
    pending = {p['request_id']: p for p in (data.get('pending_actions') or [])}
    action_results = data.get('action_results', [])

    events = []
    for ar in action_results:
        rid = ar.get('request_id')
        res = ar.get('result', {})
        p = pending.get(rid)
        if not p:
            continue
        rec = {
            'turn': turn,
            'tactic': None,
            'unit': p.get('unit'),
            'card_title': p.get('card', {}).get('title') if isinstance(p.get('card'), dict) else None,
            'initiative': p.get('initiative'),
            'behavior': p.get('behavior'),
            'details': res,
        }
        events.append({'event': 'action_resolved', 'action_resolved': rec})

    # Any pending actions not provided: mark resolved_by_client_without_details
    for rid, p in pending.items():
        if not any(r.get('request_id') == rid for r in action_results):
            rec = {
                'turn': turn,
                'tactic': None,
                'unit': p.get('unit'),
                'card_title': p.get('card', {}).get('title') if isinstance(p.get('card'), dict) else None,
                'initiative': p.get('initiative'),
                'behavior': p.get('behavior'),
                'details': {'note': 'resolved_by_client_without_details'}
            }
            events.append({'event': 'action_resolved', 'action_resolved': rec})

    return jsonify({'ok': True, 'events': events})


@app.route('/api/remove_unit_stateless', methods=['POST'])
def remove_unit_stateless():
    """Stateless removal of an AI unit from a provided ai_units list.

    Expected JSON: { ai_units: [{name, aggression, ...}], unit_name }
    Returns: { ok: true, removed_unit, remaining_units }
    """
    data = request.get_json(force=True) or {}
    ai_units_payload = data.get('ai_units') or []
    unit_name = data.get('unit_name')
    if not unit_name:
        return jsonify({'error': 'unit_name required'}), 400

    remaining = [u for u in ai_units_payload if (u.get('name') if isinstance(u, dict) else str(u)) != unit_name]
    remaining_units = [{'name': u.get('name') if isinstance(u, dict) else str(u), 'aggression': u.get('aggression') if isinstance(u, dict) else None} for u in remaining]
    evt = {'event': 'unit_removed', 'turn': data.get('turn'), 'unit_name': unit_name, 'reason': 'killed_by_player'}
    return jsonify({'ok': True, 'removed_unit': unit_name, 'remaining_units': remaining_units, 'event': evt})


if __name__ == '__main__':
    # bind to 0.0.0.0 so the app is reachable from nginx in docker-compose
    app.run(host='0.0.0.0', port=5000, debug=True)
