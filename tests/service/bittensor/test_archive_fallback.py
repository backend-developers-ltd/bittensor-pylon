"""
Tests for AbstractBittensorClient.archive_fallback method.

These tests verify the archive fallback logic that determines whether to use the main client
or the archive client based on block age and availability.
"""

import ipaddress

import pytest
from turbobt.substrate.exceptions import UnknownBlock

from pylon.service.bittensor.models import AxonInfo, AxonProtocol, Block, BlockHash, Coldkey, Hotkey, Neuron
from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def test_neuron():
    return Neuron(
        uid=1,
        coldkey=Coldkey("coldkey_1"),
        hotkey=Hotkey("test_hotkey"),
        active=True,
        axon_info=AxonInfo(ip=ipaddress.IPv4Address("192.168.1.1"), port=8080, protocol=AxonProtocol.TCP),
        stake=100.0,
        rank=0.5,
        emission=10.0,
        incentive=0.8,
        consensus=0.9,
        trust=0.7,
        validator_trust=0.6,
        dividends=0.4,
        last_update=1000,
        validator_permit=True,
        pruning_score=50,
    )


@pytest.fixture
def main_client():
    """
    Create a main MockBittensorClient instance.
    """
    return MockBittensorClient()


@pytest.fixture
def archive_client():
    """
    Create an archive MockBittensorClient instance.
    """
    return MockBittensorClient()


@pytest.fixture
def main_client_with_archive(main_client, archive_client):
    """
    Configure main client with archive client and default cutoff.
    """
    main_client.archive_client = archive_client
    main_client.archive_blocks_cutoff = 300
    return main_client


@pytest.mark.asyncio
async def test_archive_fallback_no_archive_client(main_client, test_neuron):
    """
    Test that main client is used when no archive client is configured, even for old blocks.
    """
    expected_neurons = [test_neuron]
    old_block = Block(number=100, hash=BlockHash("0xold"))
    latest_block = Block(number=500, hash=BlockHash("0xlatest"))

    async with main_client:
        async with main_client.mock_behavior(
            get_latest_block=[latest_block],
            _get_neurons=[expected_neurons],
        ):
            result = await main_client.get_neurons(netuid=1, block=old_block)

    assert result == expected_neurons
    assert main_client.calls["_get_neurons"] == [(1, old_block)]


@pytest.mark.asyncio
async def test_archive_fallback_block_none(main_client_with_archive, archive_client, test_neuron):
    """
    Test that main client is used when block is None (query for latest).
    """
    expected_neurons = [test_neuron]

    async with main_client_with_archive, archive_client:
        async with main_client_with_archive.mock_behavior(
            _get_neurons=[expected_neurons],
        ):
            result = await main_client_with_archive.get_neurons(netuid=1, block=None)

    assert result == expected_neurons
    assert main_client_with_archive.calls["get_latest_block"] == []
    assert main_client_with_archive.calls["_get_neurons"] == [(1, None)]
    assert archive_client.calls["_get_neurons"] == []


@pytest.mark.asyncio
async def test_archive_fallback_recent_block_main_succeeds(main_client_with_archive, archive_client, test_neuron):
    """
    Test that main client is used for recent blocks when it succeeds.
    """
    recent_block = Block(number=450, hash=BlockHash("0xrecent"))
    latest_block = Block(number=500, hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with main_client_with_archive, archive_client:
        async with main_client_with_archive.mock_behavior(
            get_latest_block=[latest_block],
            _get_neurons=[expected_neurons],
        ):
            result = await main_client_with_archive.get_neurons(netuid=1, block=recent_block)

    assert result == expected_neurons
    assert main_client_with_archive.calls["get_latest_block"] == [()]
    assert main_client_with_archive.calls["_get_neurons"] == [(1, recent_block)]
    assert archive_client.calls["_get_neurons"] == []


@pytest.mark.asyncio
async def test_archive_fallback_unknown_block_fallback(main_client_with_archive, archive_client, test_neuron):
    """
    Test that archive client is used when main client raises UnknownBlock.
    """
    recent_block = Block(number=450, hash=BlockHash("0xrecent"))
    latest_block = Block(number=500, hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with main_client_with_archive, archive_client:
        async with (
            main_client_with_archive.mock_behavior(
                get_latest_block=[latest_block],
                _get_neurons=[UnknownBlock()],
            ),
            archive_client.mock_behavior(
                _get_neurons=[expected_neurons],
            ),
        ):
            result = await main_client_with_archive.get_neurons(netuid=1, block=recent_block)

    assert result == expected_neurons
    assert main_client_with_archive.calls["get_latest_block"] == [()]
    assert main_client_with_archive.calls["_get_neurons"] == [(1, recent_block)]
    assert archive_client.calls["_get_neurons"] == [(1, recent_block)]


@pytest.mark.asyncio
async def test_archive_fallback_exact_cutoff_boundary(main_client_with_archive, archive_client, test_neuron):
    """
    Test behavior when block is exactly at the cutoff boundary.
    """
    boundary_block = Block(number=200, hash=BlockHash("0xboundary"))
    latest_block = Block(number=500, hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with main_client_with_archive, archive_client:
        async with main_client_with_archive.mock_behavior(
            get_latest_block=[latest_block],
            _get_neurons=[expected_neurons],
        ):
            result = await main_client_with_archive.get_neurons(netuid=1, block=boundary_block)

    assert result == expected_neurons
    assert main_client_with_archive.calls["_get_neurons"] == [(1, boundary_block)]
    assert archive_client.calls["_get_neurons"] == []


@pytest.mark.asyncio
async def test_archive_fallback_one_past_cutoff_boundary(main_client_with_archive, archive_client, test_neuron):
    """
    Test behavior when block is one past the cutoff boundary (should use archive).
    """
    past_cutoff_block = Block(number=199, hash=BlockHash("0xpast"))
    latest_block = Block(number=500, hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with main_client_with_archive, archive_client:
        async with (
            main_client_with_archive.mock_behavior(
                get_latest_block=[latest_block],
            ),
            archive_client.mock_behavior(
                _get_neurons=[expected_neurons],
            ),
        ):
            result = await main_client_with_archive.get_neurons(netuid=1, block=past_cutoff_block)

    assert result == expected_neurons
    assert main_client_with_archive.calls["_get_neurons"] == []
    assert archive_client.calls["_get_neurons"] == [(1, past_cutoff_block)]


@pytest.mark.asyncio
async def test_archive_fallback_custom_cutoff(main_client, archive_client, test_neuron):
    """
    Test that custom archive_blocks_cutoff value is respected.
    """
    main_client.archive_client = archive_client
    main_client.archive_blocks_cutoff = 100

    old_block = Block(number=350, hash=BlockHash("0xold"))
    latest_block = Block(number=500, hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with main_client, archive_client:
        async with (
            main_client.mock_behavior(
                get_latest_block=[latest_block],
            ),
            archive_client.mock_behavior(
                _get_neurons=[expected_neurons],
            ),
        ):
            result = await main_client.get_neurons(netuid=1, block=old_block)

    assert result == expected_neurons
    assert main_client.calls["get_latest_block"] == [()]
    assert main_client.calls["_get_neurons"] == []
    assert archive_client.calls["_get_neurons"] == [(1, old_block)]
