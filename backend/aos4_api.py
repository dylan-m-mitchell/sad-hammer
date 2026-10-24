"""Flask API for the player-facing Age of Sigmar 4th game.

The engine stays framework-agnostic.  This module owns only the transport
concerns: a small in-memory game store, JSON request parsing and HTTP errors.
Active games are cached because a full five-round state is roughly 150 KB;
versioned JSON export/import keeps games portable and lets the client survive a
server restart.
"""

from __future__ import annotations

import secrets
from collections import OrderedDict
from functools import lru_cache
from threading import RLock
from typing import Any, Dict, Mapping, Optional, Tuple
from uuid import uuid4

from flask import Blueprint, Response, jsonify, request

from backend.engine.systems.aos4.datapack import (
    DataPackError,
    list_faction_packs,
    list_missions,
    load_faction_pack,
    load_mission,
)
from backend.engine.systems.aos4.play import Aos4Match, MatchError, build_options
from backend.engine.systems.base import IllegalActionError

aos4_api = Blueprint("aos4_api", __name__, url_prefix="/api/aos4")
ResponseReturn = Tuple[Response, int] | Response

_MAX_GAMES = 32
_GAMES: "OrderedDict[str, Aos4Match]" = OrderedDict()
_LOCK = RLock()


class GameNotFoundError(KeyError):
    """Raised when a game id is not in the in-memory store."""


def _reset_games() -> None:
    """Clear the in-memory store (used by tests)."""

    with _LOCK:
        _GAMES.clear()


def _put_game(match: Aos4Match) -> Aos4Match:
    with _LOCK:
        _GAMES[match.game_id] = match
        _GAMES.move_to_end(match.game_id)
        while len(_GAMES) > _MAX_GAMES:
            _GAMES.popitem(last=False)
    return match


def _get_game(game_id: str) -> Aos4Match:
    with _LOCK:
        match = _GAMES.get(game_id)
        if match is None:
            raise GameNotFoundError(game_id)
        _GAMES.move_to_end(game_id)
        return match


def _json_error(
    message: str,
    *,
    status: int = 400,
    issues: Optional[list] = None,
) -> Tuple[Response, int]:
    payload: Dict[str, Any] = {"error": message}
    if issues:
        payload["issues"] = issues
    return jsonify(payload), status


def _body() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, Mapping):
        return {}
    return dict(payload)


def _boolean(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)


def _integer(value: Any, name: str, *, minimum: int, maximum: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= result <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return result


@lru_cache(maxsize=1)
def _options_payload() -> Dict[str, Any]:
    packs = [load_faction_pack(pack_id) for pack_id in list_faction_packs()]
    missions = [load_mission(mission_id) for mission_id in list_missions()]
    return build_options(packs, missions)


def _snapshot_response(
    match: Aos4Match,
    *,
    events: Optional[list] = None,
    decisions: Optional[list] = None,
) -> ResponseReturn:
    return jsonify(match.snapshot(events=events or [], decisions=decisions or []))


@aos4_api.get("/options")
def options() -> ResponseReturn:
    try:
        return jsonify(_options_payload())
    except (DataPackError, ValueError) as exc:
        return _json_error(str(exc), status=500)


@aos4_api.post("/games")
def create_game() -> ResponseReturn:
    body = _body()
    try:
        seed = (
            _integer(body["seed"], "seed", minimum=0, maximum=2_147_483_647)
            if body.get("seed") not in (None, "")
            else secrets.randbelow(1_000_000)
        )
        mission = str(body.get("mission") or "contested-ground")
        player_pack = str(body.get("player_pack") or "stormcast-starter")
        ai_pack = str(body.get("ai_pack") or "skaven-starter")
        skip_deployment = _boolean(body.get("skip_deployment"), True)
        max_rounds: Optional[int] = None
        if body.get("max_rounds") not in (None, ""):
            max_rounds = _integer(body["max_rounds"], "max_rounds", minimum=1, maximum=20)
        game_id = f"aos4-{uuid4().hex[:12]}"
        match = Aos4Match.create(
            seed=seed,
            mission=mission,
            player_pack=player_pack,
            ai_pack=ai_pack,
            max_rounds=max_rounds,
            skip_deployment=skip_deployment,
            game_id=game_id,
        )
        _put_game(match)
        return _snapshot_response(match)
    except (DataPackError, MatchError, ValueError) as exc:
        return _json_error(str(exc))


@aos4_api.get("/games/<game_id>")
def get_game(game_id: str) -> ResponseReturn:
    try:
        match = _get_game(game_id)
        return _snapshot_response(match)
    except GameNotFoundError:
        return _json_error(f"game {game_id!r} was not found", status=404)


@aos4_api.delete("/games/<game_id>")
def delete_game(game_id: str) -> ResponseReturn:
    with _LOCK:
        if game_id not in _GAMES:
            return _json_error(f"game {game_id!r} was not found", status=404)
        del _GAMES[game_id]
    return jsonify({"deleted": game_id})


@aos4_api.post("/games/<game_id>/actions")
def apply_action(game_id: str) -> ResponseReturn:
    body = _body()
    action = body.get("action")
    if not isinstance(action, Mapping):
        return _json_error("the request body must contain an 'action' object")
    with _LOCK:
        try:
            match = _get_game(game_id)
            events, decisions = match.apply_player_action(dict(action))
            return _snapshot_response(match, events=events, decisions=decisions)
        except GameNotFoundError:
            return _json_error(f"game {game_id!r} was not found", status=404)
        except IllegalActionError as exc:
            issues = (
                [issue.to_dict() for issue in exc.validation.errors]
                if exc.validation is not None
                else None
            )
            return _json_error(str(exc), issues=issues)
        except (MatchError, ValueError, KeyError, TypeError) as exc:
            return _json_error(str(exc))
        except RuntimeError as exc:
            return _json_error(str(exc), status=409)


@aos4_api.post("/games/<game_id>/resume")
def resume_game(game_id: str) -> ResponseReturn:
    with _LOCK:
        try:
            match = _get_game(game_id)
            events, decisions = match.resume()
            return _snapshot_response(match, events=events, decisions=decisions)
        except GameNotFoundError:
            return _json_error(f"game {game_id!r} was not found", status=404)
        except (MatchError, ValueError, RuntimeError) as exc:
            return _json_error(str(exc), status=409)


@aos4_api.get("/games/<game_id>/export")
def export_game(game_id: str) -> ResponseReturn:
    try:
        match = _get_game(game_id)
        text = match.session.to_json(indent=2)
        return Response(
            text,
            mimetype="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{game_id}.json"',
            },
        )
    except GameNotFoundError:
        return _json_error(f"game {game_id!r} was not found", status=404)


@aos4_api.post("/games/import")
def import_game() -> ResponseReturn:
    body = _body()
    raw_state = body.get("state") if isinstance(body.get("state"), Mapping) else body
    if not isinstance(raw_state, Mapping):
        return _json_error("the request body must contain a saved game state")
    try:
        game_id = f"aos4-import-{uuid4().hex[:12]}"
        match = Aos4Match.from_state(
            raw_state,
            game_id=game_id,
        )
        events, decisions = match.resume()
        _put_game(match)
        return _snapshot_response(match, events=events, decisions=decisions)
    except (DataPackError, MatchError, ValueError, KeyError, TypeError) as exc:
        return _json_error(f"could not import the saved game: {exc}")
    except RuntimeError as exc:
        return _json_error(f"could not import the saved game: {exc}", status=409)


__all__ = ["aos4_api"]
