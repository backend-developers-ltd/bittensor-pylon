"""
Pytest fixtures for testing TurboBtClient with mocked turbobt library dependencies.

These fixtures mock the entire turbobt call chain using `create_autospec()`, which automatically
creates AsyncMock for async methods and preserves method signatures.

Usage:
    Use `turbobt_client` fixture in your tests and configure mock behavior in test-specific
    fixtures that wrap the base fixtures (block_spec, subnet_spec, neuron_spec).

Example:
    @pytest.fixture
    def subnet_spec(subnet_spec):
        subnet_spec.list_neurons.return_value = [neuron1, neuron2]
        return subnet_spec

    @pytest.mark.asyncio
    async def test_get_neurons(turbobt_client, subnet_spec):
        result = await turbobt_client.get_neurons(netuid=1)
        assert len(result) == 2
"""

from unittest.mock import create_autospec

import pytest
import pytest_asyncio
from turbobt import Bittensor
from turbobt import BlockReference as TurboBtBlockReference
from turbobt import Subnet as TurboBtSubnet
from turbobt.neuron import NeuronReference as TurboBtNeuronReference
from turbobt.subnet import SubnetNeurons as TurboBtSubnetNeurons
from turbobt.subnet import SubnetWeights as TurboBtSubnetWeights

from pylon.service.bittensor.client import TurboBtClient


@pytest.fixture
def block_spec():
    return create_autospec(TurboBtBlockReference, instance=True)


@pytest.fixture
def neuron_spec():
    return create_autospec(TurboBtNeuronReference, instance=True)


@pytest.fixture
def subnet_spec(neuron_spec):
    subnet_mock = create_autospec(TurboBtSubnet, instance=True)
    # Manually add attributes with proper autospec
    subnet_mock.neurons = create_autospec(TurboBtSubnetNeurons, instance=True)
    subnet_mock.weights = create_autospec(TurboBtSubnetWeights, instance=True)
    subnet_mock.neuron.return_value = neuron_spec
    return subnet_mock


@pytest.fixture
def bittensor_spec(block_spec, subnet_spec):
    bittensor_mock = create_autospec(Bittensor, instance=True)
    bittensor_mock.__aenter__.return_value = bittensor_mock
    # Add specs for nested objects returned by methods.
    bittensor_mock.block.return_value = block_spec
    bittensor_mock.subnet.return_value = subnet_spec
    # Create a spec for a class itself.
    bittensor_class_mock = create_autospec(Bittensor)
    bittensor_class_mock.return_value = bittensor_mock
    return bittensor_class_mock


@pytest_asyncio.fixture
async def turbobt_client(monkeypatch, bittensor_spec, wallet):
    from pylon._internal.common.types import BittensorNetwork

    monkeypatch.setattr("pylon.service.bittensor.client.Bittensor", bittensor_spec)
    async with TurboBtClient(wallet=wallet, uri=BittensorNetwork("ws://testserver")) as client:
        yield client


@pytest_asyncio.fixture
async def turbobt_client_no_wallet(monkeypatch, bittensor_spec):
    from pylon._internal.common.types import BittensorNetwork

    monkeypatch.setattr("pylon.service.bittensor.client.Bittensor", bittensor_spec)
    async with TurboBtClient(wallet=None, uri=BittensorNetwork("ws://testserver")) as client:
        yield client
