import pytest
from litestar.testing import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.app.state.latest_block = 12
        test_client.app.state.current_epoch_start = 35736
        yield test_client


def test_weights__set_update_requests(client):
    hotkey = "hotkey"
    initial_weight = 2.0
    delta = 3.5

    # Set initial weight
    resp = client.put("/set_weight", json={"hotkey": hotkey, "weight": initial_weight})
    assert resp.status_code == 200
    assert resp.json()["weight"] == initial_weight

    # Update weight (add delta)
    resp2 = client.put("/update_weight", json={"hotkey": hotkey, "weight_delta": delta})
    assert resp2.status_code == 200
    assert resp2.json()["weight"] == initial_weight + delta

    # Check raw weights
    resp3 = client.get("/raw_weights")
    assert resp3.status_code == 200
    weights = resp3.json()["weights"]
    assert weights[hotkey] == initial_weight + delta

    # Query with missing epoch should not find it
    resp4 = client.get("/raw_weights?epoch=1")
    assert resp4.status_code == 404


def test_set_weights__missing_params(client):
    # Missing hotkey
    resp = client.put("/set_weight", json={"weight": 1.0})
    assert resp.status_code == 400
    assert resp.json().get("detail", "").startswith("Missing hotkey")
    # Missing weight
    resp2 = client.put("/set_weight", json={"hotkey": "foo"})
    assert resp2.status_code == 400
    assert resp2.json().get("detail", "").startswith("Missing weight")


def test_update_weight__missing_params(client):
    # Missing hotkey
    resp = client.put("/update_weight", json={"weight_delta": 1.0})
    assert resp.status_code == 400
    assert resp.json().get("detail", "").startswith("Missing hotkey")
    # Missing weight_delta
    resp2 = client.put("/update_weight", json={"hotkey": "foo"})
    assert resp2.status_code == 400
    assert resp2.json().get("detail", "").startswith("Missing weight_delta")
