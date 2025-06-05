import pytest
from litestar.testing import TestClient

from app.main import app
from tests.conftest import get_mock_metagraph


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.app.state.latest_block = 123
        test_client.app.state.metagraph_cache = {123: get_mock_metagraph()}
        yield test_client


def test_latest_metagraph__success(client):
    resp = client.get("/metagraph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["block"] == 123
    assert data["block_hash"] == "0xabc"
    assert len(data["neurons"]) == 3


def test_latest_metagraph__no_block(client):
    client.app.state.latest_block = None
    resp = client.get("/metagraph")
    assert resp.status_code == 500


def test_metagraph__block_number_success(client):
    resp = client.get("/metagraph/123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["block"] == 123
    assert data["block_hash"] == "0xabc"
    assert len(data["neurons"]) == 3


def test_latest_block_success(client):
    resp = client.get("/latest_block")
    assert resp.status_code == 200
    data = resp.json()
    assert data["block"] == 123


def test_latest_block_no_block(client):
    client.app.state.latest_block = None
    resp = client.get("/latest_block")
    assert resp.status_code == 500


def test_block_hash_success(client):
    resp = client.get("/block_hash/123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["block_hash"] == "0xabc"
