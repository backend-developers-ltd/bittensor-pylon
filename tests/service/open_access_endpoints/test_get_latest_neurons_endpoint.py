"""
Tests for the GET /subnet/{netuid}/neurons/latest endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import (
    Block,
    Neuron,
    SubnetNeurons,
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
async def test_get_latest_neurons_open_access_success(
    test_client: AsyncTestClient,
    open_access_mock_bt_client: MockBittensorClient,
    subnet_neurons: SubnetNeurons,
    block: Block,
):
    """
    Test getting the latest neurons successfully.
    """
    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_neurons=[subnet_neurons],
    ):
        response = await test_client.get("/api/v1/subnet/1/neurons/latest")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == subnet_neurons.model_dump(mode="json")

    assert open_access_mock_bt_client.calls["get_block"] == []
    assert open_access_mock_bt_client.calls["get_latest_block"] == [()]
    assert open_access_mock_bt_client.calls["get_neurons"] == [(1, block)]


@pytest.mark.asyncio
async def test_get_latest_neurons_open_access_empty_neurons(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient, block: Block
):
    """
    Test getting the latest neurons when the subnet has no neurons.
    """
    subnet_neurons = SubnetNeurons(block=block, neurons={})

    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[block],
        get_neurons=[subnet_neurons],
    ):
        response = await test_client.get("/api/v1/subnet/2/neurons/latest")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == subnet_neurons.model_dump(mode="json")
