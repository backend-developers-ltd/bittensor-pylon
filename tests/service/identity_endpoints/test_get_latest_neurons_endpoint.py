"""
Tests for the GET /identity/{identity_name}/subnet/{netuid}/neurons/latest endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import (
    Block,
    Neuron,
    SubnetNeurons,
)
from pylon._internal.common.types import (
    BlockHash,
    BlockNumber,
)
from tests.factories import BlockFactory, NeuronFactory
from tests.mock_bittensor_client import MockBittensorClient


@pytest.fixture
def block(block_factory: BlockFactory) -> Block:
    return block_factory.build()


@pytest.fixture
def neurons(neuron_factory: NeuronFactory):
    return neuron_factory.batch(2)


@pytest.fixture
def subnet_neurons(neurons: list[Neuron], block: Block):
    return SubnetNeurons(block=block, neurons={neuron.hotkey: neuron for neuron in neurons})


@pytest.mark.asyncio
async def test_get_latest_neurons_identity_success(
    test_client: AsyncTestClient,
    sn1_mock_bt_client: MockBittensorClient,
    subnet_neurons: SubnetNeurons,
    block: Block,
):
    """
    Test getting the latest neurons successfully.
    """
    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_neurons=[subnet_neurons],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/neurons/latest")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == subnet_neurons.model_dump(mode="json")

    assert sn1_mock_bt_client.calls["get_block"] == []
    assert sn1_mock_bt_client.calls["get_latest_block"] == [()]
    assert sn1_mock_bt_client.calls["get_neurons"] == [(1, block)]


@pytest.mark.asyncio
async def test_get_latest_neurons_identity_empty_neurons(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient
):
    """
    Test getting the latest neurons when the subnet has no neurons.
    """
    block = Block(number=BlockNumber(100), hash=BlockHash("0x123abc"))
    neurons = SubnetNeurons(block=block, neurons={})

    async with sn2_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_neurons=[neurons],
    ):
        response = await test_client.get("/api/v1/identity/sn2/subnet/2/neurons/latest")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == {
            "block": {"number": 100, "hash": "0x123abc"},
            "neurons": {},
        }
