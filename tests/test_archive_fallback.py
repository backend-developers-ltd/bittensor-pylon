from unittest.mock import AsyncMock, patch

import pytest
from turbobt.substrate.exceptions import UnknownBlock

from pylon_common.settings import settings
from pylon_service.bittensor_client import cache_metagraph
from tests.conftest import MockSubnet, get_mock_turbo_neuron


@pytest.fixture
def mock_app(test_client):
    test_client.app.state.latest_block = 1100
    return test_client.app


@pytest.fixture
def mock_list_neurons():
    with patch.object(MockSubnet, "list_neurons", new_callable=AsyncMock) as mock:
        mock.return_value = [get_mock_turbo_neuron(uid) for uid in range(3)]
        yield mock


@pytest.mark.asyncio
async def test_recent_block_uses_main_client(mock_app, mock_wallet, mock_list_neurons):
    await cache_metagraph(mock_app, block=1100, block_hash="0x44c")

    assert 1100 in mock_app.state.metagraph_cache
    mock_list_neurons.assert_called_once_with(block_hash="0x44c")
    mock_app.state.bittensor_client.subnet.assert_called_once_with(settings.bittensor_netuid)
    mock_app.state.archive_bittensor_client.subnet.assert_not_called()


@pytest.mark.asyncio
async def test_old_block_uses_archive_client(mock_app, mock_wallet, mock_list_neurons):
    await cache_metagraph(mock_app, block=799, block_hash="0x320")

    assert 799 in mock_app.state.metagraph_cache
    mock_list_neurons.assert_called_once_with(block_hash="0x320")
    mock_app.state.bittensor_client.subnet.assert_not_called()
    mock_app.state.archive_bittensor_client.subnet.assert_called_once_with(settings.bittensor_netuid)


@pytest.mark.asyncio
async def test_main_fails_fallback_to_archive(mock_app, mock_wallet, mock_list_neurons):
    mock_neurons = [get_mock_turbo_neuron(uid) for uid in range(3)]
    call_count = 0

    async def mock_list_neurons_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise UnknownBlock("Block not found")
        return mock_neurons

    mock_list_neurons.side_effect = mock_list_neurons_side_effect
    await cache_metagraph(mock_app, block=1100, block_hash="0x44c")

    assert 1100 in mock_app.state.metagraph_cache
    assert mock_list_neurons.call_count == 2
    mock_app.state.bittensor_client.subnet.assert_called_once_with(settings.bittensor_netuid)
    mock_app.state.archive_bittensor_client.subnet.assert_called_once_with(settings.bittensor_netuid)


@pytest.mark.asyncio
async def test_archive_fails_exception_reraised(mock_app, mock_wallet, mock_list_neurons):
    mock_list_neurons.side_effect = UnknownBlock("Block not found")

    with pytest.raises(UnknownBlock):
        await cache_metagraph(mock_app, block=799, block_hash="0x320")

    assert 799 not in mock_app.state.metagraph_cache
    assert mock_list_neurons.call_count == 1
    mock_app.state.bittensor_client.subnet.assert_not_called()
    mock_app.state.archive_bittensor_client.subnet.assert_called_once_with(settings.bittensor_netuid)


@pytest.mark.asyncio
async def test_no_latest_block_uses_main(mock_app, mock_wallet, mock_list_neurons):
    mock_app.state.latest_block = None

    await cache_metagraph(mock_app, block=100, block_hash="0x64")

    assert 100 in mock_app.state.metagraph_cache
    mock_list_neurons.assert_called_once_with(block_hash="0x64")
    mock_app.state.bittensor_client.subnet.assert_called_once_with(settings.bittensor_netuid)
    mock_app.state.archive_bittensor_client.subnet.assert_not_called()
