#!/usr/bin/env python3
"""Flask API (moved into backend package).

This is the same application previously at repo root `api_server.py`, but
paths are computed relative to the repository root so the module can live
inside the `backend/` package.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import tempfile
import os

from backend.battlescribe_parser import parse_battlescribe_html
from backend.full_simulator import SoloSimulator, Unit as AIUnit
from copy import deepcopy
from backend.reference_card_decks import tactic_to_actions, battleplan_deck
from backend import placement as placement_module
import json
import hashlib
import random as _random

app = Flask(__name__)
CORS(app)

# Compute repository root (one level up from this file)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Load optional battleplan -> zone bias mapping (file lives in backend/)
BATTLEPLAN_ZONE_BIAS = []
_bp_bias_path = os.path.join(os.path.dirname(__file__), 'battleplan_zone_bias.json')
try:
    with open(_bp_bias_path, 'r', encoding='utf-8') as _f:
        BATTLEPLAN_ZONE_BIAS = json.load(_f)
except Exception:
    BATTLEPLAN_ZONE_BIAS = []


def _get_zone_info_for_bp(bp):
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
    if not bp:
        return None
    # battleplans-media lives at repository root
    base_dir = os.path.join(REPO_ROOT, 'battleplans-media')
    stems = []
    try:
        title = str(bp.get('title', '')).strip()
    except Exception:
        title = ''
    if title:
        try:
            raw = title
            slug = raw.lower().replace(' ', '-').replace('/', '-').replace("'", '').replace('"', '')
            slug = __import__('re').sub(r'[^a-z0-9\-]+', '-', slug).strip('-')
            stems.append(slug)
            words = [w for w in __import__('re').split(r'[^A-Za-z0-9]+', raw) if w]
            if words:
                title_case = '-'.join([w[0].upper() + w[1:] if len(w) > 1 else w.upper() for w in words])
                stems.append(title_case)
                stems.append(title_case + '-2048x1524')
            stems.append(raw)
            stems.append(raw + '-2048x1524')
            stripped = __import__('re').sub(r'\s*\([^\)]*\)\s*', '', raw).strip()
            if stripped and stripped != raw:
                ws = [w for w in __import__('re').split(r'[^A-Za-z0-9]+', stripped) if w]
                stripped_hy = '-'.join([w[0].upper() + w[1:] if len(w) > 1 else w.upper() for w in ws])
                stems.append(stripped_hy)
                stems.append(stripped_hy + '-2048x1524')
        except Exception:
            stems = stems or []

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
    return None


# Serve the web frontend (static) from the web/ directory at repository root
@app.route('/')
def index():
    return send_from_directory(os.path.join(REPO_ROOT, 'web'), 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(REPO_ROOT, 'web'), filename)


# Serve battleplan map images from the repository `battleplans-media/` directory
@app.route('/assets/battleplan_maps/<path:filename>')
def battleplan_maps(filename):
    base = os.path.join(REPO_ROOT, 'battleplans-media')
    return send_from_directory(base, filename)


@app.route('/api/load_roster', methods=['POST'])
def load_roster():
    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    f = request.files['file']
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
    ai_units = []
    if units:
        for u in units:
            ai_units.append(AIUnit(u.get('name', 'Unit'), aggression=u.get('aggression', 'Neutral')))
    else:
        ai_units = [AIUnit('Mournfang Pack A', aggression='Aggressive'), AIUnit('Huskard on Stonehorn', aggression='Aggressive')]

    events = []
    sim = SoloSimulator(ai_units, seed=seed)
    try:
        for _ in range(turns):
            out = sim.simulate_turn()
            for ev in out:
                events.append(ev.copy())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'events': events})


@app.route('/api/battleplans', methods=['GET'])
def list_battleplans():
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


def _derive_seed(initial_seed, turn):
    if initial_seed is None:
        return _random.getrandbits(32)
    s = f"{initial_seed}:{turn}"
    h = hashlib.sha256(s.encode('utf-8')).digest()
    return int.from_bytes(h[:4], 'big')


@app.route('/api/session_stateless', methods=['POST'])
def create_session_stateless():
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

    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    roll_mode = data.get('roll_mode') if data else None
    if roll_mode not in ('ai', 'player'):
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

    seed = _random.getrandbits(32)
    sim = SoloSimulator(ai_units, seed=seed)
    placement = None
    try:
        if selected_battleplan:
            placement = placement_module.build_proposed_placement(sim.turn, sim.rng, selected_battleplan, ai_profiles)
    except Exception:
        placement = None

    # Ensure the proposed placement includes explicit, frontend-friendly battleplan info
    try:
        if placement is not None and selected_battleplan:
            # placement['battleplan'] may already contain the bp dict; normalize to include id/title/deployment/map
            placement.setdefault('battleplan', {})
            try:
                placement['battleplan']['id'] = selected_battleplan.get('id')
            except Exception:
                pass
            try:
                placement['battleplan']['title'] = selected_battleplan.get('title')
            except Exception:
                pass
            try:
                placement['battleplan']['deployment'] = selected_battleplan.get('deployment')
            except Exception:
                pass
            try:
                m = _find_map_for_bp(selected_battleplan)
                if m:
                    placement['battleplan']['map'] = m
            except Exception:
                pass
    except Exception:
        # non-fatal: don't break session creation if annotation fails
        pass

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
    data = request.get_json(force=True) or {}
    seed = data.get('seed')
    turn = int(data.get('turn', 1))
    roll_mode = data.get('roll_mode', 'ai')
    ai_units_payload = data.get('ai_units') or []

    units = []
    for u in ai_units_payload:
        name = u.get('name') if isinstance(u, dict) else str(u)
        agg = u.get('aggression') if isinstance(u, dict) else None
        agg_mod = u.get('aggression_modifier', 0) if isinstance(u, dict) else 0
        units.append(AIUnit(name, aggression=agg or 'Neutral', aggression_modifier=agg_mod))

    derived = _derive_seed(seed, turn)
    sim = SoloSimulator(units, seed=derived)
    sim.turn = turn

    events = []
    pending_actions = []

    if roll_mode == 'player':
        sim.tactics_deck.advance_turn(sim.turn)
        tactic_card = sim.choose_battle_tactic()
        if tactic_card is None:
            return jsonify({'turn': sim.turn, 'events': [{'event': 'no_tactic_available'}]})

        tactic_title = tactic_card.get('title')
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

        from backend.deck_manager import create_turn_action_assignments
        action_assignments = create_turn_action_assignments(tactic_card, sim.units, {u.name: True for u in sim.units if True}, rng=sim.rng)

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

    resolved = sim.simulate_turn()
    return jsonify({'turn': turn, 'events': resolved})


@app.route('/api/resolve_rolls_stateless', methods=['POST'])
def resolve_rolls_stateless():
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
    app.run(host='0.0.0.0', port=5000, debug=True)
