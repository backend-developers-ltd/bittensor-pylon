from unittest.mock import AsyncMock

import pytest
from litestar.testing import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pylon_common.settings import settings
from pylon_service import db
from pylon_service.main import create_app
from pylon_service.utils import get_epoch_containing_block
from tests.conftest import MockBittensorClient, get_mock_metagraph

EPOCH = 1500


@pytest.fixture
def client(monkeypatch, temp_db_config):
    # mock db uri for local unit tests
    test_db_uri = temp_db_config["db_uri"]
    monkeypatch.setattr(settings, "pylon_db_uri", test_db_uri)
    monkeypatch.setenv("PYLON_DB_URI", test_db_uri)

    new_engine = create_async_engine(test_db_uri, echo=False, future=True)
    new_session_local = async_sessionmaker(bind=new_engine, class_=AsyncSession, expire_on_commit=False)

    monkeypatch.setattr(db, "engine", new_engine)
    monkeypatch.setattr(db, "SessionLocal", new_session_local)

    monkeypatch.setattr(settings, "am_i_a_validator", True)
    test_app = create_app(tasks=[])
    with TestClient(test_app) as test_client:
        test_client.app.state.bittensor_client = MockBittensorClient()
        test_client.app.state.latest_block = EPOCH
        test_client.app.state.metagraph_cache = {EPOCH: get_mock_metagraph(EPOCH)}
        test_client.app.state.current_epoch_start = get_epoch_containing_block(EPOCH).start
        yield test_client


def test_latest_metagraph__success(client):
    resp = client.get("/latest_metagraph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["block"] == EPOCH
    assert data["block_hash"] == "0xabc"
    assert len(data["neurons"]) == 3


def test_latest_metagraph__no_block(client):
    client.app.state.latest_block = None
    resp = client.get("/latest_metagraph")
    assert resp.status_code == 500


def test_metagraph__block_success(client):
    resp = client.get(f"/metagraph/{EPOCH}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["block"] == EPOCH
    assert data["block_hash"] == "0xabc"
    assert len(data["neurons"]) == 3


def test_latest_block_success(client):
    resp = client.get("/latest_block")
    assert resp.status_code == 200
    data = resp.json()
    assert data["block"] == EPOCH


def test_latest_block_no_block(client):
    client.app.state.latest_block = None
    resp = client.get("/latest_block")
    assert resp.status_code == 500


def test_block_hash_success(client):
    resp = client.get(f"/block_hash/{EPOCH}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["block_hash"] == "0xabc"


def test_weights__set_update_requests(client):
    hotkey = "hotkey"
    initial_weight = 2.0
    delta = 3.5

    # Set initial weight
    resp = client.put("/set_weight", json={"hotkey": hotkey, "weight": initial_weight})
    assert resp.status_code == 200
    assert resp.json()["weight"] == initial_weight

    # Update weight (add delta)
    resp = client.put("/update_weight", json={"hotkey": hotkey, "weight_delta": delta})
    assert resp.status_code == 200
    assert resp.json()["weight"] == initial_weight + delta

    # Check raw weights
    resp = client.get("/latest_weights")
    assert resp.status_code == 200
    weights = resp.json()["weights"]
    assert weights[hotkey] == initial_weight + delta

    # Query with missing block should not find it
    resp = client.get("/weights/2110")
    assert resp.status_code == 404

    # Test force commit
    client.app.state.bittensor_client = MockBittensorClient()
    resp = client.post("/force_commit_weights")
    assert resp.status_code == 200
    assert resp.json()["block"] == EPOCH
    assert resp.json()["committed_weights"] is not None


def test_set_weight__missing_params(client):
    # Missing hotkey
    resp = client.put("/set_weight", json={"weight": 1.0})
    assert resp.status_code == 400
    assert "Validation failed" in resp.json().get("detail", "")
    # Missing weight
    resp = client.put("/set_weight", json={"hotkey": "foo"})
    assert resp.status_code == 400
    assert "Validation failed" in resp.json().get("detail", "")


def test_update_weight__missing_params(client):
    # Missing hotkey
    resp = client.put("/update_weight", json={"weight_delta": 1.0})
    assert resp.status_code == 400
    assert "Validation failed" in resp.json().get("detail", "")
    # Missing weight_delta
    resp = client.put("/update_weight", json={"hotkey": "foo"})
    assert resp.status_code == 400
    assert "Validation failed" in resp.json().get("detail", "")


def test_set_weights__batch_success(client):
    """Test setting multiple weights at once."""
    weights_dict = {"hotkey1": 0.6, "hotkey2": 0.4, "hotkey3": 0.8}

    resp = client.put("/set_weights", json={"weights": weights_dict})
    assert resp.status_code == 200

    response_data = resp.json()
    assert response_data["count"] == 3
    assert response_data["weights"]["hotkey1"] == 0.6
    assert response_data["weights"]["hotkey2"] == 0.4
    assert response_data["weights"]["hotkey3"] == 0.8

    # Verify weights were actually set in database
    resp = client.get("/latest_weights")
    assert resp.status_code == 200
    db_weights = resp.json()["weights"]
    assert db_weights["hotkey1"] == 0.6
    assert db_weights["hotkey2"] == 0.4
    assert db_weights["hotkey3"] == 0.8


def test_set_weights__update_existing(client):
    """Test that set_weights updates existing weights."""
    resp = client.put("/set_weight", json={"hotkey": "hotkey1", "weight": 0.3})
    assert resp.status_code == 200

    weights_dict = {
        "hotkey1": 0.7,  # update existing
        "hotkey4": 0.2,  # add new
    }

    resp = client.put("/set_weights", json={"weights": weights_dict})
    assert resp.status_code == 200

    # Check that weights were updated correctly
    resp = client.get("/latest_weights")
    assert resp.status_code == 200
    db_weights = resp.json()["weights"]
    assert db_weights["hotkey1"] == 0.7  # updated
    assert db_weights["hotkey4"] == 0.2  # new


def test_set_weights__empty_dict(client):
    """Test set_weights with empty weights dict."""
    resp = client.put("/set_weights", json={"weights": {}})
    assert resp.status_code == 400
    assert "No weights provided" in str(resp.json())


def test_set_weights__validation_errors(client):
    """Test set_weights validation errors with specific messages."""
    # Missing weights field
    resp = client.put("/set_weights", json={})
    assert resp.status_code == 400
    assert "Validation failed" in resp.json().get("detail", "")

    # Empty hotkey
    resp = client.put("/set_weights", json={"weights": {"": 0.5}})
    assert resp.status_code == 400
    response_text = str(resp.json())
    assert "Invalid hotkey" in response_text
    assert "must be a non-empty string" in response_text


def test_validator_endpoints_forbidden(client, monkeypatch):
    """
    Tests that weight-setting endpoints are forbidden when not in validator mode.
    """
    monkeypatch.setattr(settings, "am_i_a_validator", False)
    resp = client.put("/set_weight", json={"hotkey": "foo", "weight": 1.0})
    assert resp.status_code == 403

    resp = client.put("/update_weight", json={"hotkey": "foo", "weight_delta": 1.0})
    assert resp.status_code == 403

    weights_data = {"foo": 1.0}
    resp = client.put("/set_weights", json={"weights": weights_data})
    assert resp.status_code == 403

    resp = client.post("/force_commit_weights")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_commitment(client):
    netuid = settings.bittensor_netuid
    bt_client = client.app.state.bittensor_client
    mock_get_commitment = bt_client.subnet(netuid).commitments.get
    mock_fetch_commitments = bt_client.subnet(netuid).commitments.fetch

    mock_get_commitment.return_value = b"0x1234"
    hotkey = "hotkey"
    resp = client.get(f"/commitment/{hotkey}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hotkey"] == hotkey
    assert data["commitment"] is not None

    mock_get_commitment.return_value = None
    resp = client.get("/commitment/hotkey_not_found")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]

    mock_fetch_commitments.return_value = {"hotkey": b"0x1234"}
    resp = client.get("/commitments")
    assert resp.status_code == 200
    assert resp.json().keys() is not None


@pytest.mark.asyncio
async def test_set_commitment(client):
    netuid = settings.bittensor_netuid
    bt_client = client.app.state.bittensor_client
    bt_client.subnet(netuid).commitments.set.return_value = AsyncMock()

    resp = client.post("/set_commitment", json={"data_hex": "4466"})
    assert resp.status_code == 200

    resp = client.post("/set_commitment", json={})
    assert resp.status_code == 400
    assert "Validation failed" in resp.json()["detail"]

    resp = client.post("/set_commitment", json={"data_hex": "333"})
    assert resp.status_code == 400
    response_text = str(resp.json())
    assert "Invalid 'data_hex'" in response_text
