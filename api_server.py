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
import uuid
from threading import Lock
import json

app = Flask(__name__)
CORS(app)

# In-memory sessions: session_id -> {'sim': SoloSimulator, 'ai_units': [AIUnit], 'ai_profiles': [...], 'log': []}
SESSIONS = {}
SESSIONS_LOCK = Lock()

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

    # Accept optional roll handling selection from JSON payload: 'roll_mode' with values 'ai' or 'player'
    # If provided via multipart/form-data (file upload) the client should include a form field 'roll_mode'
    roll_mode = None
    # Check JSON body first
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    if data and 'roll_mode' in data:
        roll_mode = data.get('roll_mode')
    else:
        # check form data (multipart)
        if 'roll_mode' in request.form:
            roll_mode = request.form.get('roll_mode')

    # Normalize roll_mode; default to 'ai' (AI handles its own rolls)
    if roll_mode not in ('ai', 'player'):
        roll_mode = 'ai'

    # Accept optional battleplan selection (by id or title) from JSON/form
    chosen_bp = None
    # check JSON body first
    if data and 'battleplan' in data:
        chosen_bp = data.get('battleplan')
    else:
        if 'battleplan' in request.form:
            chosen_bp = request.form.get('battleplan')

    # Resolve chosen_bp to a battleplan card dict if possible; otherwise draw one randomly
    selected_battleplan = None
    try:
        if chosen_bp is not None:
            # allow numeric id or title
            try:
                cid = int(chosen_bp)
                selected_battleplan = next((b for b in battleplan_deck if b.get('id') == cid), None)
            except Exception:
                # treat as title match
                selected_battleplan = next((b for b in battleplan_deck if str(b.get('title')).lower() == str(chosen_bp).lower()), None)
        if not selected_battleplan:
            # choose one deterministically from sim.rng if possible, else from python random
            try:
                selected_battleplan = sim.rng.choice(battleplan_deck)
            except Exception:
                import random as _rnd
                selected_battleplan = _rnd.choice(battleplan_deck)
    except Exception:
        selected_battleplan = battleplan_deck[0] if battleplan_deck else None

    # Create SoloSimulator instance for AI units
    sim = SoloSimulator(ai_units)

    session_id = str(uuid.uuid4())
    with SESSIONS_LOCK:
        SESSIONS[session_id] = {
            'sim': sim,
            'ai_units': ai_units,
            'ai_profiles': ai_profiles,
            'log': [],
            'roll_mode': roll_mode
            , 'battleplan': selected_battleplan, 'placement_done': False
        }

    # Immediately build and persist a proposed placement for the chosen battleplan
    # so clients can show a deployment UI before the first AI turn.
    try:
        if selected_battleplan:
            placement = placement_module.build_proposed_placement(sim.turn, sim.rng, selected_battleplan, ai_profiles)
            with SESSIONS_LOCK:
                sess = SESSIONS.get(session_id)
                if sess is not None:
                    sess['proposed_placement'] = placement
                    sess['log'].append(placement)
                    # mark placement emitted so we don't duplicate on the first ai_turn
                    sess['placement_done'] = True
                    # Auto-apply placement: server chooses final zones so client is not prompted
                    try:
                        placements = []
                        allowed = placement.get('allowed_zones') or []
                        for s in placement.get('suggestions', []):
                            unit = s.get('unit')
                            zone = s.get('suggested_zone') or (allowed[0] if allowed else None)
                            placements.append({'unit': unit, 'zone': zone})
                        sess['placement_confirmed'] = {'placements': placements, 'by': 'server'}
                        evt = {'event': 'placement_confirmed', 'turn': placement.get('turn'), 'placements': placements}
                        sess['log'].append(evt)
                    except Exception:
                        # don't block session creation on placement persistence
                        pass
    except Exception:
        # don't block session creation on placement building failures
        pass

    # If a battleplan was selected, attempt to find and include its map URL
    bp_info = None
    if selected_battleplan:
        try:
            bp_info = {'id': selected_battleplan.get('id'), 'title': selected_battleplan.get('title'), 'deployment': selected_battleplan.get('deployment')}
            m = _find_map_for_bp(selected_battleplan)
            if m:
                bp_info['map'] = m
        except Exception:
            bp_info = {'id': selected_battleplan.get('id'), 'title': selected_battleplan.get('title'), 'deployment': selected_battleplan.get('deployment')}

    return jsonify({'session_id': session_id, 'battleplan': bp_info, 'state': {'turn': sim.turn, 'ai_count': len(ai_units), 'roll_mode': roll_mode}})


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
    return jsonify({'turn': sim.turn, 'ai_units': ai, 'ai_profiles': ai_profiles, 'log': sess['log'], 'roll_mode': sess.get('roll_mode', 'ai')})


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


@app.route('/api/session/<session_id>/ai_turn', methods=['POST'])
def ai_turn(session_id):
    """Run a single AI turn for the session and return the events produced."""
    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({'error': 'session not found'}), 404

    sim = sess['sim']
    roll_mode = sess.get('roll_mode', 'ai')

    # Server-mediated 'player' roll mode: pause before resolving actions and record pending actions
    if roll_mode == 'player':
        # Build tactic and action draws similar to SoloSimulator.simulate_turn but stop before resolving
        # We'll replicate the essential parts so we don't advance sim.turn until resolution completes.
        tactic = sim.choose_battle_tactic()
        events = []
        if tactic is None:
            events.append({"event": "no_tactic_available"})
            sess['log'].extend(events)
            sess['last_turn'] = sim.turn
            sess['last_turn_events'] = events
            text = 'No AI tactics available.\n\n'
            return (text, 200, {'Content-Type': 'text/plain; charset=utf-8'})

        action_deck = sim.build_action_deck(tactic)

        drawn_actions = []
        for u in sim.units:
            check = sim.aggression_check(u)
            will_act = check['result']
            events.append({
                "event": "aggression_check",
                "unit": u.name,
                "aggression_check": will_act,
                "roll": check['roll'],
                "modifier": check['modifier'],
                "total": check['total'],
                "target": check['target'],
            })
            if will_act:
                if not action_deck:
                    action_deck = deepcopy(tactic_to_actions.get(tactic, []))
                    sim.rng.shuffle(action_deck)
                card = action_deck.pop(0)
                # create a pending action request id
                req_id = f"{sim.turn}-{len(drawn_actions)}"
                # default dice descriptor: 1 d6 (can be enhanced later per-card)
                drawn_actions.append({
                    "request_id": req_id,
                    "unit": u.name,
                    "card": card,
                    "initiative": card.get('initiative', 0),
                    "behavior": card.get('behavior'),
                    "dice": {"count": 1, "sides": 6}
                })

        # If no drawn actions were produced (rare due to RNG), ensure the player
        # path still yields a roll_request by forcing the first unit to have one
        # pending action. This prevents flaky tests and surfaces a roll request
        # for the UI to resolve.
        if not drawn_actions and sim.units:
            u = sim.units[0]
            # ensure action_deck has at least one card
            if not action_deck:
                action_deck = deepcopy(tactic_to_actions.get(tactic, []))
                sim.rng.shuffle(action_deck)
            if action_deck:
                card = action_deck.pop(0)
            else:
                card = {'title': 'Default Action', 'initiative': 0, 'behavior': 'action'}
            req_id = f"{sim.turn}-forced-0"
            drawn_actions.append({
                "request_id": req_id,
                "unit": u.name,
                "card": card,
                "initiative": card.get('initiative', 0),
                "behavior": card.get('behavior'),
                "dice": {"count": 1, "sides": 6}
            })
            # also append an aggression_check event showing the unit acts
            events.append({
                "event": "aggression_check",
                "unit": u.name,
                "aggression_check": True,
                "roll": None,
                "modifier": getattr(u, 'aggression_modifier', 0),
                "total": None,
                "target": None,
            })

        # store paused turn info in session so resolve_rolls can continue
        paused = {
            'turn': sim.turn,
            'tactic': tactic,
            'pending_actions': drawn_actions,
        }
        sess['paused_turn'] = paused

        # Add a roll_request-like event so clients know what to resolve
        events.append({
            "event": "roll_request",
            "turn": sim.turn,
            "tactic": tactic,
            "pending_actions": [
                {
                    "request_id": a['request_id'],
                    "unit": a['unit'],
                    "card_title": a['card'].get('title'),
                    "initiative": a['initiative'],
                    "behavior": a['behavior'],
                    "dice": a.get('dice', {"count": 1, "sides": 6})
                } for a in drawn_actions
            ]
        })

        # append to log and set last turn events (paused)
        sess['log'].extend(events)
        sess['last_turn'] = sim.turn
        sess['last_turn_events'] = events

        # Return a human-readable summary that instructs the player to provide roll results
        lines = [f"=== AI Turn {sim.turn} (awaiting player rolls) ==="]
        for e in events:
            if e.get('event') == 'aggression_check':
                act = 'ACT' if e['aggression_check'] else 'HOLD'
                lines.append(f"AI check: {e['unit']} -> {act} (d6={e['roll']} + mod={e['modifier']} => total={e['total']} vs target={e['target']})")
        lines.append('\nPending actions:')
        for a in drawn_actions:
            lines.append(f"- {a['unit']} -> {a['card'].get('title')} (req={a['request_id']}) init={a['initiative']} behavior={a['behavior']}")

        text = '\n'.join(lines) + '\n\n'
        # If this is the initial turn, include placement suggestions based on chosen battleplan
        try:
            if sim.turn == 1 and sess.get('battleplan') and not sess.get('placement_done'):
                bp = sess.get('battleplan')
                # Build the proposed placement via the placement module (centralized logic)
                try:
                    placement = placement_module.build_proposed_placement(sim.turn, sim.rng, bp, sess.get('ai_profiles', []))
                except Exception:
                    # fallback to a minimal placement structure if the module fails
                    placement = {'event': 'placement', 'turn': sim.turn, 'battleplan': bp, 'allowed_zones': [], 'suggestions': []}

                sess['proposed_placement'] = placement
                sess['log'].append(placement)
                sess['placement_done'] = True
        except Exception:
            pass

        return (text, 200, {'Content-Type': 'text/plain; charset=utf-8'})

    # default 'ai' roll mode: run the full simulate_turn() and advance the turn
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


@app.route('/api/session/<session_id>/placement', methods=['GET'])
def get_session_placement(session_id):
    """Return the proposed placement for the session, if any."""
    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({'error': 'session not found'}), 404

    prop = sess.get('proposed_placement')
    confirmed = sess.get('placement_confirmed', False)
    if not prop:
        return jsonify({'placement': None, 'confirmed': False}), 200
    return jsonify({'placement': prop, 'confirmed': confirmed}), 200


@app.route('/api/session/<session_id>/placement', methods=['POST'])
def post_session_placement(session_id):
    """Accept a placement confirmation from the client and strictly validate zones.

    Expected JSON: { placements: [ { unit: <name>, zone: <zone_name> }, ... ] }
    Validation rules:
      - There must be a proposed placement on the session.
      - The client must provide a placement for every AI unit in the session.
      - Each provided zone must be one of the `allowed_zones` from the proposed placement.
    On success: stores `placement_confirmed` with the provided placements and appends a
    `placement_confirmed` event to the session log.
    """
    data = request.get_json(force=True) or {}
    placements = data.get('placements')
    if placements is None:
        return jsonify({'error': 'placements required'}), 400

    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
        if not sess:
            return jsonify({'error': 'session not found'}), 404

        prop = sess.get('proposed_placement')
        if not prop:
            return jsonify({'error': 'no proposed placement to confirm'}), 400

        # If server already auto-confirmed placement, disallow client confirmation
        if sess.get('placement_confirmed') and sess.get('placement_confirmed', {}).get('by') == 'server':
            return jsonify({'error': 'placement_already_auto_confirmed'}), 400

        # Use the placement module to validate submitted placements
        ok, err = placement_module.validate_placements(prop, placements)
        if not ok:
            return jsonify(err), 400

        # Persist confirmed placements
        sess['placement_confirmed'] = {'placements': placements, 'by': 'client'}
        # Append confirmation event to the log
        evt = {'event': 'placement_confirmed', 'turn': prop.get('turn'), 'placements': placements}
        sess['log'].append(evt)

    return jsonify({'ok': True, 'placements': placements}), 200


@app.route('/api/session/<session_id>/resolve_rolls', methods=['POST'])
def resolve_rolls(session_id):
    """Accept player-provided roll/action results to finish a paused AI turn.

    Expected JSON: { "action_results": [ { "request_id": "<id>", "result": { ... } }, ... ] }
    The server will match request_id to paused pending_actions and produce final action_resolved events.
    """
    data = request.get_json(force=True) or {}
    action_results = data.get('action_results', [])

    # Validate incoming roll values: known d6-like keys must be integers in 1..6
    D6_KEYS = {'roll', 'to_hit', 'to_wound', 'save', 'value'}

    def _is_int_like(v):
        try:
            if isinstance(v, bool):
                return False
            int(v)
            return True
        except Exception:
            return False

    for ar in action_results:
        rid = ar.get('request_id')
        res = ar.get('result', {}) or {}
        if not isinstance(res, dict):
            continue
        # Walk top-level result fields and validate numeric die-like entries
        for k, v in res.items():
            # if key indicates a die roll or ends with _roll, treat as d6 unless specified otherwise
            if k in D6_KEYS or (isinstance(k, str) and k.endswith('_roll')):
                # allow a single int or a list of ints
                if isinstance(v, (list, tuple)):
                    for item in v:
                        if not _is_int_like(item):
                            return jsonify({'error': 'invalid_roll_value', 'request_id': rid, 'field': k, 'value': item}), 400
                        iv = int(item)
                        if iv < 1 or iv > 6:
                            return jsonify({'error': 'roll_out_of_range', 'request_id': rid, 'field': k, 'value': iv}), 400
                else:
                    if not _is_int_like(v):
                        return jsonify({'error': 'invalid_roll_value', 'request_id': rid, 'field': k, 'value': v}), 400
                    iv = int(v)
                    if iv < 1 or iv > 6:
                        return jsonify({'error': 'roll_out_of_range', 'request_id': rid, 'field': k, 'value': iv}), 400

    with SESSIONS_LOCK:
        sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({'error': 'session not found'}), 404

    paused = sess.get('paused_turn')
    if not paused:
        return jsonify({'error': 'no paused turn to resolve'}), 400

    sim = sess['sim']
    pending = {p['request_id']: p for p in paused.get('pending_actions', [])}

    events = []
    # Build resolved events using provided results when available
    for ar in action_results:
        rid = ar.get('request_id')
        res = ar.get('result', {})
        pending_action = pending.get(rid)
        if not pending_action:
            continue
        rec = {
            'turn': paused.get('turn'),
            'tactic': paused.get('tactic'),
            'unit': pending_action.get('unit'),
            'card_title': pending_action.get('card', {}).get('title'),
            'initiative': pending_action.get('initiative'),
            'behavior': pending_action.get('behavior'),
            'details': res,
        }
        events.append({'event': 'action_resolved', 'action_resolved': rec})

    # For any pending actions not provided in action_results, mark as client-resolved with no details
    for rid, p in pending.items():
        if not any(r.get('request_id') == rid for r in action_results):
            rec = {
                'turn': paused.get('turn'),
                'tactic': paused.get('tactic'),
                'unit': p.get('unit'),
                'card_title': p.get('card', {}).get('title'),
                'initiative': p.get('initiative'),
                'behavior': p.get('behavior'),
                'details': {'note': 'resolved_by_client_without_details'}
            }
            events.append({'event': 'action_resolved', 'action_resolved': rec})

    # Append events to session log and mark last_turn
    sess['log'].extend(events)
    sess['last_turn'] = paused.get('turn')
    sess['last_turn_events'] = events

    # Clear paused_turn and advance simulator turn counter
    sess.pop('paused_turn', None)
    sim.turn = sim.turn + 1

    return jsonify({'ok': True, 'events': events})


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
