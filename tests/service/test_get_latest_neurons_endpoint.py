from ipaddress import IPv4Address

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    Neuron,
    Stakes,
    SubnetNeurons,
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
    NeuronActive,
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
            emission=Emission(Tao(neuron_data["emission"])),
            incentive=Incentive(neuron_data["incentive"]),
            consensus=Consensus(neuron_data["consensus"]),
            trust=Trust(neuron_data["trust"]),
            validator_trust=ValidatorTrust(neuron_data["validator_trust"]),
            dividends=Dividends(neuron_data["dividends"]),
            last_update=Timestamp(neuron_data["last_update"]),
            validator_permit=ValidatorPermit(neuron_data["validator_permit"]),
            pruning_score=PruningScore(neuron_data["pruning_score"]),
            stakes=Stakes(
                alpha=AlphaStake(Tao(neuron_data["stakes"]["alpha"])),
                tao=TaoStake(Tao(neuron_data["stakes"]["tao"])),
                total=TotalStake(Tao(neuron_data["stakes"]["total"])),
            ),
        )

    return SubnetNeurons(
        block=block,
        neurons=neurons,
    )


@pytest.mark.asyncio
async def test_get_latest_neurons_success(
    test_client: AsyncTestClient,
    mock_bt_client: MockBittensorClient,
    neurons: SubnetNeurons,
    block: Block,
    neurons_json: dict,
):
    async with mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_neurons=[neurons],
    ):
        response = await test_client.get("/api/v1/neurons/latest")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == neurons_json

    assert mock_bt_client.calls["get_block"] == []
    assert mock_bt_client.calls["get_latest_block"] == [()]
    assert mock_bt_client.calls["get_neurons"] == [(settings.bittensor_netuid, block)]


@pytest.mark.asyncio
async def test_get_latest_neurons_empty_neurons(test_client: AsyncTestClient, mock_bt_client: MockBittensorClient):
    block = Block(number=BlockNumber(100), hash=BlockHash("0x123abc"))
    neurons = SubnetNeurons(block=block, neurons={})

    async with mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_neurons=[neurons],
    ):
        response = await test_client.get("/api/v1/neurons/latest")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == {
            "block": {"number": 100, "hash": "0x123abc"},
            "neurons": {},
        }
