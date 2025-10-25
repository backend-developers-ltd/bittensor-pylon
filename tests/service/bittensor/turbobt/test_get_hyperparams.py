import pytest

from pylon.service.bittensor.models import SubnetHyperparams


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.get_hyperparameters.return_value = {
        "max_weights_limit": 100,
        "commit_reveal_weights_enabled": True,
    }
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_hyperparams(turbobt_client, subnet_spec):
    result = await turbobt_client._get_hyperparams(netuid=1)
    assert result == SubnetHyperparams(
        max_weights_limit=100,
        commit_reveal_weights_enabled=True,
    )


@pytest.mark.asyncio
async def test_turbobt_client_get_hyperparams_returns_none_when_no_params(turbobt_client, subnet_spec):
    subnet_spec.get_hyperparameters.return_value = None
    result = await turbobt_client._get_hyperparams(netuid=1)
    assert result is None
