"""
Tests for BittensorClient delegation logic.

These tests verify the delegation logic in BittensorClient._delegate() that determines whether to use
the main client or the archive client based on block age and availability.
"""

import ipaddress

import pytest
from bittensor_wallet import Wallet
from turbobt.substrate.exceptions import UnknownBlock

from pylon._internal.common.currency import Currency, Token
from pylon._internal.common.models import AxonInfo, AxonProtocol, Block, Neuron, Stakes
from pylon._internal.common.types import (
    AlphaStake,
    ArchiveBlocksCutoff,
    BittensorNetwork,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    Emission,
    Hotkey,
    Incentive,
    NetUid,
    NeuronActive,
    NeuronUid,
    Port,
    PruningScore,
    Rank,
    Stake,
    TaoStake,
    Timestamp,
    TotalStake,
    Trust,
    ValidatorPermit,
    ValidatorTrust,
)
from pylon.service.bittensor.client import BittensorClient
from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def test_neuron():
    return Neuron(
        uid=NeuronUid(1),
        coldkey=Coldkey("coldkey_1"),
        hotkey=Hotkey("test_hotkey"),
        active=NeuronActive(True),
        axon_info=AxonInfo(ip=ipaddress.IPv4Address("192.168.1.1"), port=Port(8080), protocol=AxonProtocol.TCP),
        stake=Stake(100.0),
        rank=Rank(0.5),
        emission=Emission(Currency[Token.ALPHA](10.0)),
        incentive=Incentive(0.8),
        consensus=Consensus(0.9),
        trust=Trust(0.7),
        validator_trust=ValidatorTrust(0.6),
        dividends=Dividends(0.4),
        last_update=Timestamp(1000),
        validator_permit=ValidatorPermit(True),
        pruning_score=PruningScore(50),
        stakes=Stakes(
            alpha=AlphaStake(Currency[Token.ALPHA](75.0)),
            tao=TaoStake(Currency[Token.TAO](25.0)),
            total=TotalStake(Currency[Token.ALPHA](100.0)),
        ),
    )


@pytest.fixture
def bittensor_client():
    wallet = Wallet()

    # Create BittensorClient
    client = BittensorClient(
        wallet=wallet,
        uri=BittensorNetwork("ws://main"),
        archive_uri=BittensorNetwork("ws://archive"),
        archive_blocks_cutoff=ArchiveBlocksCutoff(300),
        subclient_cls=MockBittensorClient,
    )
    return client


@pytest.fixture
def main_client(bittensor_client):
    return bittensor_client._main_client


@pytest.fixture
def archive_client(bittensor_client):
    return bittensor_client._archive_client


@pytest.mark.asyncio
async def test_delegation_recent_block_uses_main_client(bittensor_client, main_client, archive_client, test_neuron):
    """
    Test that main client is used for recent blocks when it succeeds.
    """
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with bittensor_client:
        async with main_client.mock_behavior(
            get_latest_block=[latest_block],
            get_neurons=[expected_neurons],
        ):
            result = await bittensor_client.get_neurons_list(netuid=NetUid(1), block=recent_block)

    assert result == expected_neurons
    assert main_client.calls["get_latest_block"] == [()]
    assert main_client.calls["get_neurons"] == [(1, recent_block)]
    assert archive_client.calls["get_neurons"] == []


@pytest.mark.asyncio
async def test_delegation_unknown_block_falls_back_to_archive(
    bittensor_client, main_client, archive_client, test_neuron
):
    """
    Test that archive client is used when main client raises UnknownBlock.
    """
    recent_block = Block(number=BlockNumber(450), hash=BlockHash("0xrecent"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with bittensor_client:
        async with (
            main_client.mock_behavior(
                get_latest_block=[latest_block],
                get_neurons=[UnknownBlock()],
            ),
            archive_client.mock_behavior(
                get_neurons=[expected_neurons],
            ),
        ):
            result = await bittensor_client.get_neurons_list(netuid=NetUid(1), block=recent_block)

    assert result == expected_neurons
    assert main_client.calls["get_latest_block"] == [()]
    assert main_client.calls["get_neurons"] == [(1, recent_block)]
    assert archive_client.calls["get_neurons"] == [(1, recent_block)]


@pytest.mark.asyncio
async def test_delegation_exact_cutoff_boundary_uses_main_client(
    bittensor_client, main_client, archive_client, test_neuron
):
    """
    Test behavior when block is exactly at the cutoff boundary (should use main).
    """
    boundary_block = Block(number=BlockNumber(200), hash=BlockHash("0xboundary"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with bittensor_client:
        async with main_client.mock_behavior(
            get_latest_block=[latest_block],
            get_neurons=[expected_neurons],
        ):
            result = await bittensor_client.get_neurons_list(netuid=NetUid(1), block=boundary_block)

    assert result == expected_neurons
    assert main_client.calls["get_neurons"] == [(1, boundary_block)]
    assert archive_client.calls["get_neurons"] == []


@pytest.mark.asyncio
async def test_delegation_past_cutoff_boundary_uses_archive_client(
    bittensor_client, main_client, archive_client, test_neuron
):
    """
    Test behavior when block is one past the cutoff boundary (should use archive).
    """
    past_cutoff_block = Block(number=BlockNumber(199), hash=BlockHash("0xpast"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with bittensor_client:
        async with (
            main_client.mock_behavior(
                get_latest_block=[latest_block],
            ),
            archive_client.mock_behavior(
                get_neurons=[expected_neurons],
            ),
        ):
            result = await bittensor_client.get_neurons_list(netuid=NetUid(1), block=past_cutoff_block)

    assert result == expected_neurons
    assert main_client.calls["get_neurons"] == []
    assert archive_client.calls["get_neurons"] == [(1, past_cutoff_block)]


@pytest.mark.asyncio
async def test_delegation_with_custom_cutoff(bittensor_client, main_client, archive_client, test_neuron):
    """
    Test that custom archive_blocks_cutoff value is respected.
    """
    bittensor_client._archive_blocks_cutoff = ArchiveBlocksCutoff(100)

    old_block = Block(number=BlockNumber(350), hash=BlockHash("0xold"))
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))
    expected_neurons = [test_neuron]

    async with bittensor_client:
        async with (
            main_client.mock_behavior(
                get_latest_block=[latest_block],
            ),
            archive_client.mock_behavior(
                get_neurons=[expected_neurons],
            ),
        ):
            result = await bittensor_client.get_neurons_list(netuid=NetUid(1), block=old_block)

    assert result == expected_neurons
    assert main_client.calls["get_latest_block"] == [()]
    assert main_client.calls["get_neurons"] == []
    assert archive_client.calls["get_neurons"] == [(1, old_block)]


@pytest.mark.asyncio
async def test_delegation_without_block_uses_main_client(bittensor_client, main_client, archive_client):
    """
    Test that operations without block parameter always use main client.
    """
    latest_block = Block(number=BlockNumber(500), hash=BlockHash("0xlatest"))

    async with bittensor_client:
        async with main_client.mock_behavior(
            get_latest_block=[latest_block],
        ):
            result = await bittensor_client.get_latest_block()

    assert result == latest_block
    assert main_client.calls["get_latest_block"] == [()]
    assert archive_client.calls["get_latest_block"] == []
