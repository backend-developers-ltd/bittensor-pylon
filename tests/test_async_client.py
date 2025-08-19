import json

import pytest
from httpx import HTTPStatusError

from pylon_client.async_client import AsyncPylonClient
from pylon_common.constants import (
    ENDPOINT_COMMITMENT,
    ENDPOINT_HYPERPARAMS,
    ENDPOINT_LATEST_BLOCK,
    ENDPOINT_SET_WEIGHT,
    endpoint_name,
)

MOCK_DATA_PATH = "./tests/mock_data.json"
MOCK_DATA = json.load(open(MOCK_DATA_PATH))


@pytest.fixture
def mock_pylon_client() -> AsyncPylonClient:
    """Fixture to set up the mock Pylon API environment."""
    client = AsyncPylonClient(mock_data_path=MOCK_DATA_PATH)
    assert client.mock is not None
    return client


@pytest.mark.asyncio
async def test_pylon_client_get_latest_block(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly get the latest block."""
    async with mock_pylon_client as client:
        response = await client.get_latest_block()
        assert response == MOCK_DATA["metagraph"]["block"]
    client.mock.latest_block.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_metagraph(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly get the metagraph."""
    async with mock_pylon_client as client:
        response = await client.get_metagraph()
        assert response is not None
        assert response.block == MOCK_DATA["metagraph"]["block"]
        assert len(response.neurons) == len(MOCK_DATA["metagraph"]["neurons"])
    client.mock.latest_metagraph.assert_called_with()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_block_hash(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly get a block hash."""
    async with mock_pylon_client as client:
        block = MOCK_DATA["metagraph"]["block"]
        response = await client.get_block_hash(block)
        assert response == MOCK_DATA["metagraph"]["block_hash"]
    client.mock.block_hash.assert_called_with(block=block)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_epoch(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly get epoch information."""
    async with mock_pylon_client as client:
        response = await client.get_epoch()
        assert response is not None
        assert response.start == MOCK_DATA["epoch"]["start"]
        assert response.end == MOCK_DATA["epoch"]["end"]
    client.mock.epoch.assert_called_with(block=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_hyperparams(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly get hyperparameters."""
    async with mock_pylon_client as client:
        response = await client.get_hyperparams()
        assert response is not None
        assert response == MOCK_DATA["hyperparams"]
    client.mock.hyperparams.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_set_hyperparam(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly set a hyperparameter."""
    async with mock_pylon_client as client:
        response = await client.set_hyperparam("tempo", 120)
        assert response is None
    client.mock.set_hyperparam.assert_called_with(name="tempo", value=120)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_weights(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly get weights."""
    async with mock_pylon_client as client:
        response = await client.get_weights()
        assert response is not None
        assert response == {"epoch": 1440, "weights": MOCK_DATA["weights"]}
    client.mock.weights.assert_called_with(block=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_force_commit_weights(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can force commit weights."""
    async with mock_pylon_client as client:
        response = await client.force_commit_weights()
        assert response is not None
        assert response["detail"] == "Weights committed successfully"
    client.mock.force_commit_weights.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_commitment(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly get a commitment."""
    hotkey = "hotkey2"
    async with mock_pylon_client as client:
        response = await client.get_commitment(hotkey)
        expected = MOCK_DATA["commitments"][hotkey]
        assert response == expected
    client.mock.commitment.assert_called_with(hotkey=hotkey, block=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_get_commitments(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly get all commitments."""
    async with mock_pylon_client as client:
        response = await client.get_commitments()
        assert response is not None
        assert response == MOCK_DATA["commitments"]
    client.mock.commitments.assert_called_with(block=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_override_response(mock_pylon_client: AsyncPylonClient):
    """Tests that a default mock response can be overridden for a specific test."""
    new_block = 99999
    mock_pylon_client.override(endpoint_name(ENDPOINT_LATEST_BLOCK), {"block": new_block})  # type: ignore
    async with mock_pylon_client as client:
        response = await client.get_latest_block()
        assert response == new_block
    client.mock.latest_block.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_handles_error(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient correctly handles an error response from the server."""
    mock_pylon_client.override(  # type: ignore
        endpoint_name(ENDPOINT_LATEST_BLOCK), {"detail": "Internal Server Error"}, status_code=500
    )
    async with mock_pylon_client as client:
        with pytest.raises(HTTPStatusError):
            await client.get_latest_block()
    client.mock.latest_block.assert_called_once()  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_set_weight(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly set a weight."""
    async with mock_pylon_client as client:
        response = await client.set_weight("some_hotkey", 0.5)
        assert response is not None
        assert response["detail"] == "Weight set successfully"
    client.mock.set_weight.assert_called_with(hotkey="some_hotkey", weight=0.5)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_set_weights(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly set multiple weights at once."""
    weights = {"hotkey1": 0.6, "hotkey2": 0.4}
    async with mock_pylon_client as client:
        response = await client.set_weights(weights)
        assert response is not None
        assert response["count"] == 2
        assert response["weights"]["hotkey1"] == 0.6
        assert response["weights"]["hotkey2"] == 0.4
        assert response["epoch"] == 1440
    client.mock.set_weights.assert_called_with(weights=weights)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_update_weight(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly update a weight."""
    async with mock_pylon_client as client:
        response = await client.update_weight("some_hotkey", 0.1)
        assert response is not None
        assert response["detail"] == "Weight updated successfully"
    client.mock.update_weight.assert_called_with(hotkey="some_hotkey", weight_delta=0.1)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_set_commitment(mock_pylon_client: AsyncPylonClient):
    """Tests that the AsyncPylonClient can correctly set a commitment."""
    async with mock_pylon_client as client:
        response = await client.set_commitment("0x1234")
        assert response is None
    client.mock.set_commitment.assert_called_with(data_hex="0x1234")  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_override_get_commitment(mock_pylon_client: AsyncPylonClient):
    """Tests that the get_commitment mock response can be overridden."""
    hotkey = "hotkey_override"
    commitment = "0xdeadbeef"
    mock_pylon_client.override(endpoint_name(ENDPOINT_COMMITMENT), {"hotkey": hotkey, "commitment": commitment})  # type: ignore
    async with mock_pylon_client as client:
        response = await client.get_commitment(hotkey)
        assert response == commitment
    client.mock.commitment.assert_called_with(hotkey=hotkey, block=None)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_override_set_weight(mock_pylon_client: AsyncPylonClient):
    """Tests that the set_weight mock response can be overridden."""
    mock_pylon_client.override(endpoint_name(ENDPOINT_SET_WEIGHT), {"detail": "Custom success message"})  # type: ignore
    async with mock_pylon_client as client:
        response = await client.set_weight("some_hotkey", 0.99)
        assert response is not None
        assert response["detail"] == "Custom success message"
    client.mock.set_weight.assert_called_with(hotkey="some_hotkey", weight=0.99)  # type: ignore


@pytest.mark.asyncio
async def test_pylon_client_override_error_response(mock_pylon_client: AsyncPylonClient):
    """Tests that an error response can be injected for any endpoint."""
    mock_pylon_client.override(endpoint_name(ENDPOINT_HYPERPARAMS), {"detail": "Forbidden"}, status_code=403)  # type: ignore
    async with mock_pylon_client as client:
        with pytest.raises(HTTPStatusError) as exc_info:
            await client.get_hyperparams()
        assert exc_info.value.response.status_code == 403
    client.mock.hyperparams.assert_called_once()  # type: ignore
