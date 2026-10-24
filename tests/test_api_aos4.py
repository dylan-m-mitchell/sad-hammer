"""Integration tests for the player-facing AoS 4th HTTP API."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import pytest

from backend.aos4_api import _reset_games
from backend.api_server import app


@pytest.fixture(autouse=True)
def clean_game_store() -> None:
    _reset_games()
    yield
    _reset_games()


@pytest.fixture
def client():
    return app.test_client()


def _create_game(client, **overrides: Any) -> Dict[str, Any]:
    payload = {
        "seed": 7,
        "ai_profile": "balanced",
        "max_rounds": 2,
    }
    payload.update(overrides)
    response = client.post("/api/aos4/games", json=payload)
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _choose_player_action(view: Dict[str, Any]) -> Dict[str, Any]:
    actions = view["legal_actions"]
    assert actions, f"no actions for {view['interaction']} {view['phase_name']}"
    priority = ("fight", "shoot", "charge", "move", "run", "retreat", "deploy", "command")
    for action_type in priority:
        for entry in actions:
            if entry["action_type"] == action_type:
                return entry
    return actions[-1]


def _play_to_completion(
    client, game_id: str, limit: int = 500
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    snapshot = client.get(f"/api/aos4/games/{game_id}").get_json()
    responses: List[Dict[str, Any]] = []
    for _ in range(limit):
        view = snapshot["view"]
        assert view["interaction"] in (
            "player_turn",
            "player_combat_response",
            "game_over",
        )
        if view["status"] == "complete":
            return snapshot, responses
        entry = _choose_player_action(view)
        response = client.post(
            f"/api/aos4/games/{game_id}/actions",
            json={"action": entry["action"]},
        )
        assert response.status_code == 200, response.get_json()
        snapshot = response.get_json()
        responses.append(snapshot)
    raise AssertionError("game did not complete within the action limit")


def test_options_lists_starter_content(client) -> None:
    response = client.get("/api/aos4/options")
    assert response.status_code == 200
    data = response.get_json()
    pack_ids = {pack["id"] for pack in data["packs"]}
    mission_ids = {mission["id"] for mission in data["missions"]}
    profile_ids = {profile["id"] for profile in data["profiles"]}
    assert {"stormcast-starter", "skaven-starter"} <= pack_ids
    assert "contested-ground" in mission_ids
    assert {"aggressive", "balanced", "cautious"} <= profile_ids


def test_create_game_returns_player_turn_and_actions(client) -> None:
    data = _create_game(client)
    view = data["view"]
    assert data["state"]["game_id"] == data["game_id"]
    assert view["interaction"] == "player_turn"
    assert view["phase"] == "start_of_turn"
    assert view["round"] == 1
    assert view["scores"] == {"player": 0, "ai": 0}
    assert len(view["units"]) == 11
    assert len(view["objectives"]) == 4
    assert any(action["action_type"] == "end_phase" for action in view["legal_actions"])
    assert view["ai_profile"]["name"] == "balanced"


def test_human_action_advances_phase_without_ai_actions(client) -> None:
    data = _create_game(client)
    game_id = data["game_id"]
    end_phase = next(
        action for action in data["view"]["legal_actions"] if action["action_type"] == "end_phase"
    )
    response = client.post(
        f"/api/aos4/games/{game_id}/actions", json={"action": end_phase["action"]}
    )
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result["view"]["phase"] == "hero"
    assert result["view"]["interaction"] == "player_turn"
    assert result["ai_decisions"] == []
    assert any(event["kind"] == "phase_started" for event in result["events"])


def test_ai_takes_its_turn_and_explains_decisions(client) -> None:
    data = _create_game(client, max_rounds=3)
    game_id = data["game_id"]
    snapshot = data
    decisions: List[Dict[str, Any]] = []
    for _ in range(80):
        view = snapshot["view"]
        if view["status"] == "complete" or decisions:
            break
        end_phase = next(
            (entry for entry in view["legal_actions"] if entry["action_type"] == "end_phase"),
            None,
        )
        if end_phase is None:
            entry = _choose_player_action(view)
        else:
            entry = end_phase
        response = client.post(
            f"/api/aos4/games/{game_id}/actions", json={"action": entry["action"]}
        )
        assert response.status_code == 200, response.get_json()
        snapshot = response.get_json()
        decisions.extend(snapshot["ai_decisions"])
    assert decisions, "the AI never took an action"
    assert all(decision["reason"] for decision in decisions)
    assert all(decision["profile"] == "balanced" for decision in decisions)
    assert snapshot["view"]["active_side"] == "player" or snapshot["view"]["status"] == "complete"


def test_full_game_against_ai_completes(client) -> None:
    data = _create_game(client, seed=11, ai_profile="aggressive", max_rounds=2)
    game_id = data["game_id"]
    final, responses = _play_to_completion(client, game_id)
    assert final["view"]["status"] == "complete"
    assert final["view"]["interaction"] == "game_over"
    assert final["view"]["result"] in ("Victory", "Defeat", "Draw")
    assert final["view"]["legal_actions"] == []
    assert any(response["ai_decisions"] for response in responses)
    assert final["view"]["event_count"] > 20
    assert final["state"]["schema_version"] == 1


def test_manual_deployment_uses_player_owned_actions(client) -> None:
    data = _create_game(client, skip_deployment=False)
    game_id = data["game_id"]
    view = data["view"]
    assert view["phase"] == "deployment"
    assert view["interaction"] == "player_turn"
    assert view["setup"]["skip_deployment"] is False
    deploy = next(action for action in view["legal_actions"] if action["action_type"] == "deploy")
    assert deploy["actor_id"].startswith("player-")

    response = client.post(f"/api/aos4/games/{game_id}/actions", json={"action": deploy["action"]})
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result["view"]["phase"] == "deployment"
    deployed = next(unit for unit in result["view"]["units"] if unit["id"] == deploy["actor_id"])
    assert "Deployed" in deployed["status"]


def test_cannot_control_an_ai_unit(client) -> None:
    data = _create_game(client)
    game_id = data["game_id"]
    ai_unit = next(unit for unit in data["view"]["units"] if unit["side"] == "ai")
    action = {
        "action_type": "move",
        "actor_id": ai_unit["id"],
        "destination": {
            "x": ai_unit["position"]["x"] - 1,
            "y": ai_unit["position"]["y"],
        },
    }
    response = client.post(f"/api/aos4/games/{game_id}/actions", json={"action": action})
    assert response.status_code == 400
    assert "AI opponent" in response.get_json()["error"]


def test_export_and_import_round_trip(client) -> None:
    data = _create_game(client)
    game_id = data["game_id"]
    export = client.get(f"/api/aos4/games/{game_id}/export")
    assert export.status_code == 200
    assert "attachment" in export.headers["Content-Disposition"]
    saved = json.loads(export.data)
    assert saved["schema_version"] == 1
    assert saved["game_id"] == game_id

    imported = client.post("/api/aos4/games/import", json=saved)
    assert imported.status_code == 200, imported.get_json()
    result = imported.get_json()
    assert result["game_id"] != game_id
    assert result["view"]["round"] == data["view"]["round"]
    assert result["view"]["phase"] == data["view"]["phase"]
    assert result["view"]["interaction"] == "player_turn"


def test_import_rejects_invalid_state(client) -> None:
    response = client.post("/api/aos4/games/import", json={"system_id": "aos4"})
    assert response.status_code == 400
    assert "could not import" in response.get_json()["error"]
