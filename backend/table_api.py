"""Flask API for the stateless table companion.

The table API owns no game state.  Every plan request carries both rosters, the
round, the seed and the destroyed AI units, so the same request always returns
the same plan and the server can restart between rounds without losing
anything.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from flask import Blueprint, Response, jsonify, request

from backend.table.planner import DOCTRINE_LABELS, build_plan
from backend.table.rosters import (
    STARTER_DEFAULTS,
    RosterParseError,
    parse_roster,
    starter_rosters,
)

table_api = Blueprint("table_api", __name__, url_prefix="/api/table")
ResponseReturn = Union[Tuple[Response, int], Response]

_MAX_ROUND = 20
_MAX_SEED = 2_147_483_647


def _json_error(
    message: str,
    *,
    status: int = 400,
    issues: Optional[List[Dict[str, str]]] = None,
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


def _integer(body: Mapping[str, Any], key: str, *, minimum: int, maximum: int) -> int:
    raw = body.get(key)
    if isinstance(raw, bool) or raw is None:
        raise ValueError(f"{key} must be an integer")
    if isinstance(raw, float) and not raw.is_integer():
        raise ValueError(f"{key} must be an integer")
    try:
        value = int(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{key} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    return value


def _destroyed(body: Mapping[str, Any]) -> List[str]:
    raw = body.get("destroyed", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("destroyed must be an array of unit IDs")
    result: List[str] = []
    for index, value in enumerate(raw):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"destroyed[{index}] must be a non-empty unit ID")
        result.append(value.strip())
    return result


@table_api.get("/rosters")
def list_rosters() -> ResponseReturn:
    try:
        rosters = starter_rosters()
    except (OSError, ValueError) as exc:
        return _json_error(f"could not load the starter rosters: {exc}", status=500)
    return jsonify(
        {
            "rosters": {key: roster.to_dict() for key, roster in rosters.items()},
            "defaults": dict(STARTER_DEFAULTS),
            "doctrines": dict(DOCTRINE_LABELS),
        }
    )


@table_api.post("/rosters/validate")
def validate_roster() -> ResponseReturn:
    payload = request.get_json(silent=True)
    if not isinstance(payload, Mapping):
        return _json_error("the request body must contain a roster object")
    try:
        roster = parse_roster(payload)
    except RosterParseError as exc:
        return _json_error("the roster is not valid", issues=exc.issues)
    return jsonify({"roster": roster.to_dict()})


@table_api.post("/plan")
def plan() -> ResponseReturn:
    body = _body()
    for key in ("player_roster", "ai_roster"):
        if key not in body:
            return _json_error(f"{key} is required")

    try:
        player_roster = parse_roster(body["player_roster"])
        ai_roster = parse_roster(body["ai_roster"])
    except RosterParseError as exc:
        return _json_error("a roster is not valid", issues=exc.issues)

    try:
        round_number = _integer(body, "round", minimum=1, maximum=_MAX_ROUND)
        seed = _integer(body, "seed", minimum=0, maximum=_MAX_SEED)
        destroyed = _destroyed(body)
    except ValueError as exc:
        return _json_error(str(exc))

    try:
        result = build_plan(
            player_roster,
            ai_roster,
            round_number=round_number,
            seed=seed,
            destroyed=destroyed,
        )
    except ValueError as exc:
        return _json_error(str(exc))
    return jsonify(result)


__all__ = ["table_api"]
