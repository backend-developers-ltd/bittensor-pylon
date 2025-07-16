import json
from enum import Enum

import pytest
from httpx import HTTPStatusError

from pylon_client.client import PylonClient

MOCK_DATA_PATH = "./tests/mock_data.json"
MOCK_DATA = json.load(open(MOCK_DATA_PATH))


class Endpoint(str, Enum):
    GET_LATEST_BLOCK = "get_latest_block"
    GET_METAGRAPH = "get_metagraph"
    GET_BLOCK_HASH = "get_block_hash"
    GET_EPOCH = "get_epoch"
    GET_HYPERPARAMS = "get_hyperparams"
    SET_HYPERPARAM = "set_hyperparam"
    UPDATE_WEIGHT = "update_weight"
    SET_WEIGHT = "set_weight"
    GET_WEIGHTS = "get_weights"
    FORCE_COMMIT_WEIGHTS = "force_commit_weights"
    GET_COMMITMENT = "get_commitment"
    GET_COMMITMENTS = "get_commitments"
    SET_COMMITMENT = "set_commitment"


@pytest.fixture
def mock_pylon_client() -> PylonClient:
    """Fixture to set up the mock Pylon API environment."""
    client = PylonClient(mock_data_path=MOCK_DATA_PATH)
    assert client.mock is not None
    return client


@pytest.mark.asyncio
async def test_pylon_client_get_latest_block(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get the latest block."""
    async with mock_pylon_client as client:
        response = await client.get_latest_block()
        assert response is not None
        assert response["block"] == MOCK_DATA["metagraph"]["block"]
    client.mock.get_latest_block.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_metagraph(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get the metagraph."""
    async with mock_pylon_client as client:
        response = await client.get_metagraph()
        assert response is not None
        assert response.block == MOCK_DATA["metagraph"]["block"]
        assert len(response.neurons) == len(MOCK_DATA["metagraph"]["neurons"])
    client.mock.get_metagraph.assert_called_with(block_number=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_block_hash(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get a block hash."""
    async with mock_pylon_client as client:
        block_number = MOCK_DATA["metagraph"]["block"]
        response = await client.get_block_hash(block_number)
        assert response is not None
        assert response["block_hash"] == MOCK_DATA["metagraph"]["block_hash"]
    client.mock.get_block_hash.assert_called_with(block_number=block_number)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_epoch(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get epoch information."""
    async with mock_pylon_client as client:
        response = await client.get_epoch()
        assert response is not None
        assert response.epoch_start == MOCK_DATA["epoch"]["epoch_start"]
        assert response.epoch_end == MOCK_DATA["epoch"]["epoch_end"]
    client.mock.get_epoch.assert_called_with(block_number=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_hyperparams(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get hyperparameters."""
    async with mock_pylon_client as client:
        response = await client.get_hyperparams()
        assert response is not None
        assert response == MOCK_DATA["hyperparams"]
    client.mock.get_hyperparams.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_set_hyperparam(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly set a hyperparameter."""
    async with mock_pylon_client as client:
        response = await client.set_hyperparam("tempo", 120)
        assert response is not None
        assert response["detail"] == "Hyperparameter set successfully"
    client.mock.set_hyperparam.assert_called_with(name="tempo", value=120)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_weights(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get weights."""
    async with mock_pylon_client as client:
        response = await client.get_weights()
        assert response is not None
        assert response == MOCK_DATA["weights"]
    client.mock.get_weights.assert_called_with(epoch=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_force_commit_weights(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can force commit weights."""
    async with mock_pylon_client as client:
        response = await client.force_commit_weights()
        assert response is not None
        assert response["detail"] == "Weights committed successfully"
    client.mock.force_commit_weights.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_commitment(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get a commitment."""
    hotkey = "hotkey2"
    async with mock_pylon_client as client:
        response = await client.get_commitment(hotkey)
        assert response is not None
        expected = MOCK_DATA["commitments"][hotkey]
        assert response == {"commitment": expected, "hotkey": hotkey}
    client.mock.get_commitment.assert_called_with(hotkey=hotkey, block=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_commitments(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get all commitments."""
    async with mock_pylon_client as client:
        response = await client.get_commitments()
        assert response is not None
        assert response == MOCK_DATA["commitments"]
    client.mock.get_commitments.assert_called_with(block=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_override_response(mock_pylon_client: PylonClient):
    """Tests that a default mock response can be overridden for a specific test."""
    new_block_number = 99999
    mock_pylon_client.override(Endpoint.GET_LATEST_BLOCK, {"block": new_block_number})  # type: ignore
    async with mock_pylon_client as client:
        response = await client.get_latest_block()
        assert response is not None
        assert response["block"] == new_block_number
    client.mock.get_latest_block.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_handles_error(mock_pylon_client: PylonClient):
    """Tests that the PylonClient correctly handles an error response from the server."""
    mock_pylon_client.override(  # type: ignore
        Endpoint.GET_LATEST_BLOCK, {"detail": "Internal Server Error"}, status_code=500
    )
    async with mock_pylon_client as client:
        with pytest.raises(HTTPStatusError):
            await client.get_latest_block()
    client.mock.get_latest_block.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_set_weight(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly set a weight."""
    async with mock_pylon_client as client:
        response = await client.set_weight("some_hotkey", 0.5)
        assert response is not None
        assert response["detail"] == "Weight set successfully"
    client.mock.set_weight.assert_called_with(hotkey="some_hotkey", weight=0.5)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_update_weight(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly update a weight."""
    async with mock_pylon_client as client:
        response = await client.update_weight("some_hotkey", 0.1)
        assert response is not None
        assert response["detail"] == "Weight updated successfully"
    client.mock.update_weight.assert_called_with(hotkey="some_hotkey", weight_delta=0.1)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_set_commitment(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly set a commitment."""
    async with mock_pylon_client as client:
        response = await client.set_commitment("0x1234")
        assert response is not None
        assert response["detail"] == "Commitment set successfully"
    client.mock.set_commitment.assert_called_with(data_hex="0x1234")  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_override_get_commitment(mock_pylon_client: PylonClient):
    """Tests that the get_commitment mock response can be overridden."""
    hotkey = "hotkey_override"
    commitment = "0xdeadbeef"
    mock_pylon_client.override(Endpoint.GET_COMMITMENT, {"hotkey": hotkey, "commitment": commitment})  # type: ignore
    async with mock_pylon_client as client:
        response = await client.get_commitment(hotkey)
        assert response is not None
        assert response["hotkey"] == hotkey
        assert response["commitment"] == commitment
    client.mock.get_commitment.assert_called_with(hotkey=hotkey, block=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_override_set_weight(mock_pylon_client: PylonClient):
    """Tests that the set_weight mock response can be overridden."""
    mock_pylon_client.override(Endpoint.SET_WEIGHT, {"detail": "Custom success message"})  # type: ignore
    async with mock_pylon_client as client:
        response = await client.set_weight("some_hotkey", 0.99)
        assert response is not None
        assert response["detail"] == "Custom success message"
    client.mock.set_weight.assert_called_with(hotkey="some_hotkey", weight=0.99)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_override_error_response(mock_pylon_client: PylonClient):
    """Tests that an error response can be injected for any endpoint."""
    mock_pylon_client.override(Endpoint.GET_HYPERPARAMS, {"detail": "Forbidden"}, status_code=403)  # type: ignore
    async with mock_pylon_client as client:
        with pytest.raises(HTTPStatusError) as exc_info:
            await client.get_hyperparams()
        assert exc_info.value.response.status_code == 403
    client.mock.get_hyperparams.assert_called_once()  # type: ignore
