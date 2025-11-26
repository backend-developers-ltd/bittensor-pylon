"""
Tests for the GET /subnet/{netuid}/identity/{identity_name}/neurons/{block_number} endpoint.
"""


import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
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
async def test_get_neurons_identity_with_block_number(
    test_client: AsyncTestClient,
    sn1_mock_bt_client: MockBittensorClient,
    block: Block,
    subnet_neurons: SubnetNeurons,
):
    """
    Test getting neurons for a specific block number.
    """
    block_number = block.number

    async with sn1_mock_bt_client.mock_behavior(
        get_block=[block],
        get_neurons=[subnet_neurons],
    ):
        response = await test_client.get(f"/api/v1/subnet/1/identity/sn1/neurons/{block_number}")

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == subnet_neurons.model_dump(mode="json")

    assert sn1_mock_bt_client.calls["get_block"] == [(block_number,)]
    assert sn1_mock_bt_client.calls["get_neurons"] == [(1, block)]


@pytest.mark.asyncio
async def test_get_neurons_identity_empty_neurons(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient
):
    """
    Test getting neurons when the subnet has no neurons.
    """
    block = Block(number=BlockNumber(100), hash=BlockHash("0x123abc"))
    neurons = SubnetNeurons(block=block, neurons={})

    async with sn2_mock_bt_client.mock_behavior(
        get_block=[block],
        get_neurons=[neurons],
    ):
        response = await test_client.get("/api/v1/subnet/2/identity/sn2/neurons/100")

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
async def test_get_neurons_identity_invalid_block_number_type(test_client: AsyncTestClient, invalid_block_number: str):
    """
    Test that invalid block number types return 404.
    """
    response = await test_client.get(f"/api/v1/subnet/1/identity/sn1/neurons/{invalid_block_number}")

    assert response.status_code == HTTP_404_NOT_FOUND, response.content
    assert response.json() == {
        "status_code": HTTP_404_NOT_FOUND,
        "detail": "Not Found",
    }


@pytest.mark.asyncio
async def test_get_neurons_identity_block_not_found(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient
):
    """
    Test that non-existent block returns 404.
    """
    async with sn1_mock_bt_client.mock_behavior(get_block=[None]):
        response = await test_client.get("/api/v1/subnet/1/identity/sn1/neurons/123")

        assert response.status_code == HTTP_404_NOT_FOUND, response.content
        assert response.json() == {
            "status_code": HTTP_404_NOT_FOUND,
            "detail": "Block 123 not found.",
        }

    assert sn1_mock_bt_client.calls["get_block"] == [(123,)]
