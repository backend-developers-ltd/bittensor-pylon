"""
Tests for the GET /metagraph endpoint.
"""

from ipaddress import IPv4Address

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    Metagraph,
    Neuron,
    Stakes,
)
from pylon._internal.common.settings import settings
from pylon._internal.common.types import (
    AlphaStake,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    Emission,
    Hotkey,
    Incentive,
    NeuronUid,
    Port,
    PruningScore,
    Rank,
    Stake,
    Tao,
    TaoStake,
    Timestamp,
    TotalStake,
    Trust,
    ValidatorTrust,
)
from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


@pytest.fixture
def metagraph(block):
    neuron1 = Neuron(
        uid=NeuronUid(0),
        coldkey=Coldkey("5C4hrfjw9DjXZTzV3MwzrrAr9P1MJhSrvWGWqi1eSuyUpnhM"),
        hotkey=Hotkey("5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"),
        active=True,
        axon_info=AxonInfo(ip=IPv4Address("192.168.1.1"), port=Port(8091), protocol=AxonProtocol.HTTP),
        stake=Stake(100.5),
        rank=Rank(0.95),
        emission=Emission(Tao(10.5)),
        incentive=Incentive(0.85),
        consensus=Consensus(0.9),
        trust=Trust(0.88),
        validator_trust=ValidatorTrust(0.92),
        dividends=Dividends(5.5),
        last_update=Timestamp(500),
        validator_permit=True,
        pruning_score=PruningScore(1000),
        stakes=Stakes(alpha=AlphaStake(Tao(75.0)), tao=TaoStake(Tao(45.0)), total=TotalStake(Tao(83.1))),
    )
    neuron2 = Neuron(
        uid=NeuronUid(1),
        coldkey=Coldkey("5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"),
        hotkey=Hotkey("5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"),
        active=True,
        axon_info=AxonInfo(ip=IPv4Address("192.168.1.2"), port=Port(8092), protocol=AxonProtocol.TCP),
        stake=Stake(200.75),
        rank=Rank(0.88),
        emission=Emission(Tao(12.3)),
        incentive=Incentive(0.78),
        consensus=Consensus(0.85),
        trust=Trust(0.82),
        validator_trust=ValidatorTrust(0.87),
        dividends=Dividends(6.2),
        last_update=Timestamp(501),
        validator_permit=False,
        pruning_score=PruningScore(950),
        stakes=Stakes(alpha=AlphaStake(Tao(150.0)), tao=TaoStake(Tao(90.0)), total=TotalStake(Tao(166.2))),
    )
    return Metagraph(
        block=block,
        neurons={
            neuron1.hotkey: neuron1,
            neuron2.hotkey: neuron2,
        },
    )


METAGRAPH_JSON = {
    "block": {"number": 1000, "hash": "0xabc123"},
    "neurons": {
        "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty": {
            "uid": 0,
            "coldkey": "5C4hrfjw9DjXZTzV3MwzrrAr9P1MJhSrvWGWqi1eSuyUpnhM",
            "hotkey": "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            "active": True,
            "axon_info": {"ip": "192.168.1.1", "port": 8091, "protocol": 4},
            "stake": 100.5,
            "rank": 0.95,
            "emission": 10.5,
            "incentive": 0.85,
            "consensus": 0.9,
            "trust": 0.88,
            "validator_trust": 0.92,
            "dividends": 5.5,
            "last_update": 500,
            "validator_permit": True,
            "pruning_score": 1000,
            "stakes": {"alpha": 75.0, "tao": 45.0, "total": 83.1},
        },
        "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": {
            "uid": 1,
            "coldkey": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
            "hotkey": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
            "active": True,
            "axon_info": {"ip": "192.168.1.2", "port": 8092, "protocol": 0},
            "stake": 200.75,
            "rank": 0.88,
            "emission": 12.3,
            "incentive": 0.78,
            "consensus": 0.85,
            "trust": 0.82,
            "validator_trust": 0.87,
            "dividends": 6.2,
            "last_update": 501,
            "validator_permit": False,
            "pruning_score": 950,
            "stakes": {"alpha": 150.0, "tao": 90.0, "total": 166.2},
        },
    },
}


@pytest.mark.asyncio
async def test_get_metagraph_without_block_number(
    test_client: AsyncTestClient, mock_bt_client: MockBittensorClient, metagraph: Metagraph, block: Block
):
    async with mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_metagraph=[metagraph],
    ):
        response = await test_client.get("/api/v1/metagraph")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == METAGRAPH_JSON

    assert mock_bt_client.calls["get_block"] == []
    assert mock_bt_client.calls["get_latest_block"] == [()]
    assert mock_bt_client.calls["get_metagraph"] == [(settings.bittensor_netuid, block)]


@pytest.mark.asyncio
async def test_get_metagraph_with_block_number(
    test_client: AsyncTestClient,
    mock_bt_client: MockBittensorClient,
    block: Block,
    metagraph: Metagraph,
):
    block_number = block.number

    async with mock_bt_client.mock_behavior(
        get_block=[block],
        get_metagraph=[metagraph],
    ):
        response = await test_client.get("/api/v1/metagraph", params={"block_number": block_number})

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == METAGRAPH_JSON

    assert mock_bt_client.calls["get_block"] == [(block_number,)]
    assert mock_bt_client.calls["get_metagraph"] == [(settings.bittensor_netuid, block)]


@pytest.mark.asyncio
async def test_get_metagraph_empty_neurons(test_client: AsyncTestClient, mock_bt_client: MockBittensorClient):
    block = Block(number=BlockNumber(100), hash=BlockHash("0x123abc"))
    metagraph = Metagraph(block=block, neurons={})

    async with mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_metagraph=[metagraph],
    ):
        response = await test_client.get("/api/v1/metagraph")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == {
            "block": {"number": 100, "hash": "0x123abc"},
            "neurons": {},
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_block_number",
    [
        pytest.param("not_a_number", id="string_value"),
        pytest.param("123.456", id="float_string"),
        pytest.param("true", id="boolean_string"),
    ],
)
async def test_get_metagraph_invalid_block_number_type(test_client: AsyncTestClient, invalid_block_number: str):
    response = await test_client.get("/api/v1/metagraph", params={"block_number": invalid_block_number})

    assert response.status_code == HTTP_400_BAD_REQUEST, response.content
    assert response.json() == {
        "status_code": 400,
        "detail": f"Validation failed for GET /api/v1/metagraph?block_number={invalid_block_number}",
        "extra": [{"message": "Expected `int | null`, got `str`", "key": "block_number", "source": "query"}],
    }
