"""Tests for the stateless API endpoint to remove AI units."""

import json
import pytest
from api_server import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_remove_unit_stateless_success(client):
    ai_units = [
        {"name": "Mournfang Pack A", "aggression": "Aggressive"},
        {"name": "Huskard on Stonehorn", "aggression": "Aggressive"},
    ]

    payload = {"ai_units": ai_units, "unit_name": "Huskard on Stonehorn", "turn": 3}
    resp = client.post(
        "/api/remove_unit_stateless", data=json.dumps(payload), content_type="application/json"
    )
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["ok"] is True
    assert data["removed_unit"] == "Huskard on Stonehorn"
    assert len(data["remaining_units"]) == 1


def test_remove_unit_stateless_missing_name(client):
    ai_units = [{"name": "Unit A", "aggression": "Aggressive"}]
    payload = {"ai_units": ai_units}
    resp = client.post(
        "/api/remove_unit_stateless", data=json.dumps(payload), content_type="application/json"
    )
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data.get("error") == "unit_name required"


def test_legacy_sessionful_remove_returns_410(client):
    # Legacy sessionful endpoints have been removed and should return 410
    resp = client.post(
        "/api/session/some-id/remove_unit",
        data=json.dumps({"unit_name": "X"}),
        content_type="application/json",
    )
    # endpoint removed; expect 404 Not Found
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert "removed" not in data
