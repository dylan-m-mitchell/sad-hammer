"""HTTP contract tests for the stateless table companion API."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from backend.api_server import app


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def starter_rosters(client) -> Dict[str, Any]:
    response = client.get("/api/table/rosters")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def plan_payload(client, **overrides: Any) -> Dict[str, Any]:
    data = starter_rosters(client)
    payload = {
        "player_roster": data["rosters"][data["defaults"]["player"]],
        "ai_roster": data["rosters"][data["defaults"]["ai"]],
        "round": 1,
        "seed": 7,
        "destroyed": [],
    }
    payload.update(overrides)
    return payload


def test_starter_rosters_are_preloaded(client) -> None:
    data = starter_rosters(client)
    assert set(data["rosters"]) == {"stormcast-starter", "skaven-starter"}
    assert data["defaults"] == {"player": "stormcast-starter", "ai": "skaven-starter"}
    stormcast = data["rosters"]["stormcast-starter"]
    skaven = data["rosters"]["skaven-starter"]
    assert stormcast["name"] == "Stormcast Eternals"
    assert skaven["name"] == "Skaven"
    assert len(stormcast["units"]) == 5
    assert len(skaven["units"]) == 6
    unit = stormcast["units"][0]
    assert set(unit) >= {
        "id",
        "name",
        "move",
        "save",
        "health",
        "models",
        "control",
        "keywords",
        "weapons",
    }
    assert set(unit["weapons"][0]) == {
        "name",
        "range",
        "attacks",
        "hit",
        "wound",
        "rend",
        "damage",
    }


def test_plan_returns_six_phase_cards(client) -> None:
    response = client.post("/api/table/plan", json=plan_payload(client))
    assert response.status_code == 200, response.get_json()
    plan = response.get_json()
    assert plan["round"] == 1
    assert plan["seed"] == 7
    assert plan["player_roster"]["name"] == "Stormcast Eternals"
    assert plan["ai_roster"]["name"] == "Skaven"
    assert plan["ai_roster"]["unit_count"] == 6
    assert plan["ai_roster"]["active_count"] == 6
    assert [phase["id"] for phase in plan["phases"]] == [
        "hero",
        "movement",
        "shooting",
        "charge",
        "combat",
        "end",
    ]
    for phase in plan["phases"]:
        assert phase["instructions"]
        for entry in phase["instructions"]:
            assert entry["maneuver"]
            assert entry["maneuver_name"]
            assert entry["instruction"]
            assert entry["reason"]
            assert isinstance(entry["weapons"], list)
    doctrines = {entry["doctrine"] for entry in plan["units"]}
    assert doctrines == {"press", "support", "hold"}


def test_plan_is_deterministic_for_the_same_request(client) -> None:
    payload = plan_payload(client, round=2, seed=99)
    first = client.post("/api/table/plan", json=payload)
    second = client.post("/api/table/plan", json=payload)
    assert first.status_code == 200
    assert first.get_json() == second.get_json()


def test_plan_rotates_maneuvers_between_rounds(client) -> None:
    def movement(round_number: int) -> Dict[str, str]:
        response = client.post(
            "/api/table/plan",
            json=plan_payload(client, round=round_number, seed=5),
        )
        assert response.status_code == 200
        phase = next(item for item in response.get_json()["phases"] if item["id"] == "movement")
        return {entry["unit_id"]: entry["maneuver"] for entry in phase["instructions"]}

    first = movement(1)
    second = movement(2)
    assert any(first[unit_id] != second[unit_id] for unit_id in first)


def test_destroyed_ai_units_are_filtered(client) -> None:
    response = client.post(
        "/api/table/plan",
        json=plan_payload(client, destroyed=["clanrats", "grey-seer"]),
    )
    assert response.status_code == 200, response.get_json()
    plan = response.get_json()
    remaining = {entry["id"] for entry in plan["units"]}
    assert "clanrats" not in remaining
    assert "grey-seer" not in remaining
    assert plan["ai_roster"]["active_count"] == 4
    assert set(plan["ai_roster"]["destroyed"]) == {"clanrats", "grey-seer"}
    for phase in plan["phases"]:
        for entry in phase["instructions"]:
            assert entry["unit_id"] not in {"clanrats", "grey-seer"}


def test_rosters_can_be_swapped(client) -> None:
    data = starter_rosters(client)
    payload = plan_payload(
        client,
        player_roster=data["rosters"]["skaven-starter"],
        ai_roster=data["rosters"]["stormcast-starter"],
    )
    response = client.post("/api/table/plan", json=payload)
    assert response.status_code == 200, response.get_json()
    plan = response.get_json()
    assert plan["player_roster"]["name"] == "Skaven"
    assert plan["ai_roster"]["name"] == "Stormcast Eternals"
    assert {entry["name"] for entry in plan["units"]} == {
        "Lord-Vigilant on Gryph-stalker",
        "Knight-Vexillor",
        "Liberators",
        "Reclusians",
        "Prosecutors",
    }


def test_validate_roster_returns_canonical_ids(client) -> None:
    payload = {
        "name": "My warband",
        "faction": "Order",
        "units": [
            {
                "name": "Clanrats",
                "move": "5",
                "save": 5,
                "health": 1,
                "models": 10,
                "control": 1,
                "keywords": ["Infantry"],
                "weapons": [
                    {
                        "name": "Rusty blade",
                        "range": 0,
                        "attacks": 2,
                        "hit": 4,
                        "wound": 4,
                        "rend": 0,
                        "damage": 1,
                    }
                ],
            }
        ],
    }
    response = client.post("/api/table/rosters/validate", json=payload)
    assert response.status_code == 200, response.get_json()
    roster = response.get_json()["roster"]
    assert roster["name"] == "My warband"
    assert roster["units"][0]["id"] == "clanrats"
    assert roster["units"][0]["move"] == 5


def test_validate_roster_reports_issues(client) -> None:
    response = client.post(
        "/api/table/rosters/validate",
        json={"units": [{"name": "Broken", "move": 5}]},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "the roster is not valid"
    fields = {issue["field"] for issue in payload["issues"]}
    assert "roster.units[0].save" in fields
    assert "roster.units[0].weapons" in fields


def test_plan_requires_both_rosters(client) -> None:
    payload = plan_payload(client)
    del payload["ai_roster"]
    response = client.post("/api/table/plan", json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"] == "ai_roster is required"


def test_plan_rejects_invalid_roster(client) -> None:
    response = client.post(
        "/api/table/plan",
        json=plan_payload(client, ai_roster={"units": []}),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "a roster is not valid"
    assert response.get_json()["issues"]


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"round": 0}, "round must be between 1 and 20"),
        ({"round": "one"}, "round must be an integer"),
        ({"round": 1.9}, "round must be an integer"),
        ({"round": True}, "round must be an integer"),
        ({"seed": -1}, "seed must be between 0 and 2147483647"),
        ({"seed": "many"}, "seed must be an integer"),
        ({"seed": 1.5}, "seed must be an integer"),
        ({"seed": False}, "seed must be an integer"),
        ({"destroyed": "clanrats"}, "destroyed must be an array of unit IDs"),
        ({"destroyed": [7]}, "destroyed[0] must be a non-empty unit ID"),
    ],
)
def test_plan_rejects_invalid_round_seed_and_destroyed(
    client, overrides: Dict[str, Any], message: str
) -> None:
    response = client.post("/api/table/plan", json=plan_payload(client, **overrides))
    assert response.status_code == 400
    assert response.get_json()["error"] == message


def test_plan_accepts_integer_valued_floats_and_numeric_strings(client) -> None:
    response = client.post(
        "/api/table/plan",
        json=plan_payload(client, round="2", seed=9.0),
    )
    assert response.status_code == 200, response.get_json()
    plan = response.get_json()
    assert plan["round"] == 2
    assert plan["seed"] == 9


def test_plan_ignores_unknown_destroyed_units(client) -> None:
    response = client.post(
        "/api/table/plan",
        json=plan_payload(client, destroyed=["does-not-exist"]),
    )
    assert response.status_code == 200
    plan = response.get_json()
    assert plan["ai_roster"]["destroyed"] == []
    assert plan["ai_roster"]["active_count"] == 6


def test_plan_body_must_be_json_object(client) -> None:
    response = client.post("/api/table/plan", json=[])
    assert response.status_code == 400
    assert response.get_json()["error"] == "player_roster is required"
