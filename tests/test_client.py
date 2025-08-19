import json

import pytest

from pylon_client.client import PylonClient

MOCK_DATA_PATH = "./tests/mock_data.json"
MOCK_DATA = json.load(open(MOCK_DATA_PATH))


@pytest.fixture
def mock_pylon_client() -> PylonClient:
    """Fixture to set up the mock synchronous Pylon API environment."""
    client = PylonClient(mock_data_path=MOCK_DATA_PATH)
    assert client.mock is not None
    return client


def test_pylon_client_mock_system(mock_pylon_client: PylonClient):
    """Test the new method-level mocking system for PylonClient."""
    # Returns mock data and client methods return specific types
    block = mock_pylon_client.get_latest_block()
    assert block == MOCK_DATA["metagraph"]["block"]

    metagraph = mock_pylon_client.get_metagraph()
    assert metagraph is not None
    assert metagraph.block == MOCK_DATA["metagraph"]["block"]

    # Verify the mock was called
    mock_pylon_client.mock.get_latest_block.assert_called_once()  # type: ignore
    mock_pylon_client.mock.get_metagraph.assert_called_once()  # type: ignore

    # Test override system - override responses for specific tests
    mock_pylon_client.override("get_latest_block", 99999)  # type: ignore
    overridden_block = mock_pylon_client.get_latest_block()
    assert overridden_block == 99999

    # Verify mock was called again (should be 2 times total now)
    assert mock_pylon_client.mock.get_latest_block.call_count == 2  # type: ignore
