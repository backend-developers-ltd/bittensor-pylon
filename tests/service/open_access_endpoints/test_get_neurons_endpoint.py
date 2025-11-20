"""
Tests for the GET /subnet/{netuid}/neurons/{block_number} endpoint.
"""

from ipaddress import IPv4Address

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon._internal.common.currency import Currency, Token
from pylon._internal.common.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    Neuron,
    Stakes,
    SubnetNeurons,
)
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
from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def neurons_json():
    return {
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


@pytest.fixture
def block(neurons_json):
    block_data = neurons_json["block"]
    return Block(number=BlockNumber(block_data["number"]), hash=BlockHash(block_data["hash"]))


@pytest.fixture
def neurons(neurons_json, block):
    neurons_data = neurons_json["neurons"]

    neurons = {}
    for hotkey, neuron_data in neurons_data.items():
        neurons[Hotkey(hotkey)] = Neuron(
            uid=NeuronUid(neuron_data["uid"]),
            coldkey=Coldkey(neuron_data["coldkey"]),
            hotkey=Hotkey(neuron_data["hotkey"]),
            active=NeuronActive(neuron_data["active"]),
            axon_info=AxonInfo(
                ip=IPv4Address(neuron_data["axon_info"]["ip"]),
                port=Port(neuron_data["axon_info"]["port"]),
                protocol=AxonProtocol(neuron_data["axon_info"]["protocol"]),
            ),
            stake=Stake(neuron_data["stake"]),
            rank=Rank(neuron_data["rank"]),
            emission=Emission(Currency[Token.ALPHA](neuron_data["emission"])),
            incentive=Incentive(neuron_data["incentive"]),
            consensus=Consensus(neuron_data["consensus"]),
            trust=Trust(neuron_data["trust"]),
            validator_trust=ValidatorTrust(neuron_data["validator_trust"]),
            dividends=Dividends(neuron_data["dividends"]),
            last_update=Timestamp(neuron_data["last_update"]),
            validator_permit=ValidatorPermit(neuron_data["validator_permit"]),
            pruning_score=PruningScore(neuron_data["pruning_score"]),
            stakes=Stakes(
                alpha=AlphaStake(Currency[Token.ALPHA](neuron_data["stakes"]["alpha"])),
                tao=TaoStake(Currency[Token.TAO](neuron_data["stakes"]["tao"])),
                total=TotalStake(Currency[Token.ALPHA](neuron_data["stakes"]["total"])),
            ),
        )

    return SubnetNeurons(
        block=block,
        neurons=neurons,
    )


@pytest.mark.asyncio
async def test_get_neurons_open_access_with_block_number(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    block: Block,
    neurons: SubnetNeurons,
    neurons_json: dict,
):
    """
    Test getting neurons for a specific block number.
    """
    block_number = block.number

    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block],
        get_neurons=[neurons],
    ):
        response = await test_client.get(f"/api/v1/subnet/1/neurons/{block_number}")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == neurons_json

    assert open_access_mock_bt_client.calls["get_block"] == [(block_number,)]
    assert open_access_mock_bt_client.calls["get_neurons"] == [(1, block)]


@pytest.mark.asyncio
async def test_get_neurons_open_access_empty_neurons(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient
):
    """
    Test getting neurons when the subnet has no neurons.
    """
    block = Block(number=BlockNumber(100), hash=BlockHash("0x123abc"))
    neurons = SubnetNeurons(block=block, neurons={})

    async with open_access_mock_bt_client.mock_behavior(
        get_block=[block],
        get_neurons=[neurons],
    ):
        response = await test_client.get("/api/v1/subnet/2/neurons/100")

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
async def test_get_neurons_open_access_invalid_block_number_type(
    test_client: AsyncTestClient, invalid_block_number: str
):
    """
    Test that invalid block number types return 404.
    """
    response = await test_client.get(f"/api/v1/subnet/1/neurons/{invalid_block_number}")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Not Found",
    }


@pytest.mark.asyncio
async def test_get_neurons_open_access_block_not_found(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient
):
    """
    Test that non-existent block returns 404.
    """
    async with open_access_mock_bt_client.mock_behavior(get_block=[None]):
        response = await test_client.get("/api/v1/subnet/1/neurons/123")

        assert response.status_code == HTTP_404_NOT_FOUND, response.content
        assert response.json() == {
            "status_code": HTTP_404_NOT_FOUND,
            "detail": "Block 123 not found.",
        }

    assert open_access_mock_bt_client.calls["get_block"] == [(123,)]
