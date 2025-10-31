import pytest

from pylon.service.bittensor.models import Block, BlockHash, SubnetHyperparams


@pytest.fixture
def test_block():
    return Block(number=1000, hash=BlockHash("0xabc123"))


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
        max_weights_limit=100,
        commit_reveal_weights_enabled=True,
    )


@pytest.mark.asyncio
async def test_turbobt_client_get_hyperparams_returns_none_when_no_params(turbobt_client, subnet_spec, test_block):
    subnet_spec.get_hyperparameters.return_value = None
    result = await turbobt_client.get_hyperparams(netuid=1, block=test_block)
    assert result is None
