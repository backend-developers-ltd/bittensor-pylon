import pytest

from pylon._internal.common.models import Block, CommitReveal, SubnetHyperparams
from pylon._internal.common.types import BlockHash, BlockNumber, MaxWeightsLimit


@pytest.fixture
def test_block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.get_hyperparameters.return_value = {
        "max_weights_limit": 100,
        "commit_reveal_weights_enabled": True,
    }
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_hyperparams(turbobt_client, subnet_spec, test_block):
    result = await turbobt_client.get_hyperparams(netuid=1, block=test_block)
    assert result == SubnetHyperparams(
        max_weights_limit=MaxWeightsLimit(100),
        commit_reveal_weights_enabled=CommitReveal.V4,
    )


@pytest.mark.asyncio
async def test_turbobt_client_get_hyperparams_returns_none_when_no_params(turbobt_client, subnet_spec, test_block):
    subnet_spec.get_hyperparameters.return_value = None
    result = await turbobt_client.get_hyperparams(netuid=1, block=test_block)
    assert result is None
