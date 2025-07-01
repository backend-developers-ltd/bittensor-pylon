import json

import pytest
from httpx import HTTPStatusError

from pylon_client.client import PylonClient

MOCK_DATA_PATH = "./tests/mock_data.json"
MOCK_DATA = json.load(open(MOCK_DATA_PATH))


@pytest.fixture
def mock_pylon_client() -> PylonClient:
    """Fixture to set up the mock Pylon API environment."""
    return PylonClient(mock_data_path=MOCK_DATA_PATH)


@pytest.mark.asyncio
async def test_pylon_client_get_latest_block(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get the latest block."""
    async with mock_pylon_client as client:
        response = await client.get_latest_block()
        assert response["block"] == MOCK_DATA["metagraph"]["block"]
    client.mock.get_latest_block.assert_called_once()


@pytest.mark.asyncio
async def test_pylon_client_get_metagraph(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get the metagraph."""
    async with mock_pylon_client as client:
        response = await client.get_metagraph()
        assert response.block == MOCK_DATA["metagraph"]["block"]
        assert len(response.neurons) == len(MOCK_DATA["metagraph"]["neurons"])
    client.mock.get_metagraph.assert_called_once()


@pytest.mark.asyncio
async def test_pylon_client_get_hyperparams(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly get hyperparameters."""
    async with mock_pylon_client as client:
        response = await client.get_hyperparams()
        assert response == MOCK_DATA["hyperparams"]
    client.mock.get_hyperparams.assert_called_once()


@pytest.mark.asyncio
async def test_pylon_client_override_response(mock_pylon_client: PylonClient):
    """Tests that a default mock response can be overridden for a specific test."""
    new_block_number = 99999
    mock_pylon_client.override("get_latest_block", {"block": new_block_number})

    async with mock_pylon_client as client:
        response = await client.get_latest_block()
        assert response["block"] == new_block_number
    client.mock.get_latest_block.assert_called_once()


@pytest.mark.asyncio
async def test_pylon_client_handles_error(mock_pylon_client: PylonClient):
    """Tests that the PylonClient correctly handles an error response from the server."""
    mock_pylon_client.override("get_latest_block", {"detail": "Internal Server Error"}, status_code=500)

    async with mock_pylon_client as client:
        with pytest.raises(HTTPStatusError):
            await client.get_latest_block()
    client.mock.get_latest_block.assert_called_once()


@pytest.mark.asyncio
async def test_pylon_client_set_weight(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly set a weight."""
    async with mock_pylon_client as client:
        response = await client.set_weight("some_hotkey", 0.5)
        assert response["detail"] == "Weight set successfully"
    client.mock.set_weight.assert_called_once()


@pytest.mark.asyncio
async def test_pylon_client_update_weight(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly update a weight."""
    async with mock_pylon_client as client:
        response = await client.update_weight("some_hotkey", 0.1)
        assert response["detail"] == "Weight updated successfully"
    client.mock.update_weight.assert_called_once()


@pytest.mark.asyncio
async def test_pylon_client_set_commitment(mock_pylon_client: PylonClient):
    """Tests that the PylonClient can correctly set a commitment."""
    async with mock_pylon_client as client:
        response = await client.set_commitment("0x1234")
        assert response["detail"] == "Commitment set successfully"
    client.mock.set_commitment.assert_called_once()
