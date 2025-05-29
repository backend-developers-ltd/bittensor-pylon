from unittest.mock import AsyncMock, MagicMock

from app.models import Metagraph, Neuron


class MockSubnet:
    def __init__(self, netuid=1):
        self._netuid = netuid
        self._hyperparams = {
            "rho": 10,
            "kappa": 32767,
            "tempo": 100,
            "weights_version": 0,
            "alpha_high": 58982,
            "alpha_low": 45875,
            "liquid_alpha_enabled": False,
        }

    async def get_hyperparameters(self):
        return self._hyperparams.copy()

    async def list_neurons(self, block_hash=None):
        return [get_mock_neuron() for _ in range(3)]


class MockBittensorClient:
    def __init__(self, netuid=1):
        self._netuid = netuid
        self._subnet = MockSubnet(netuid)
        self.block = MagicMock()
        self.block.return_value.get = AsyncMock(return_value=MagicMock(number=123, hash="0xabc"))
        self.head = MagicMock()
        self.head.get = AsyncMock(return_value=MagicMock(number=123, hash="0xabc"))

    def subnet(self, netuid):
        return self._subnet


def get_mock_neuron():
    return Neuron(
        uid=0,
        hotkey="mock_hotkey",
        stake=1.0,
        rank=0.5,
        trust=0.5,
        consensus=0.5,
        incentive=0.5,
        dividends=0.0,
        emission=0.1,
    )


def get_mock_metagraph():
    return Metagraph(
        block=123,
        block_hash="0xabc",
        neurons=[get_mock_neuron() for _ in range(3)],
    )
