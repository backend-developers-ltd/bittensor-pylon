from unittest.mock import AsyncMock, MagicMock

from app.models import AxonInfo, Metagraph, Neuron


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
        self.weights = AsyncMock()

    async def get_hyperparameters(self):
        return self._hyperparams.copy()

    async def list_neurons(self, block_hash=None):
        return [get_mock_neuron(uid) for uid in range(3)]


class MockBittensorClient:
    def __init__(self):
        self.block = MagicMock()
        self.block.return_value.get = AsyncMock(return_value=MagicMock(number=123, hash="0xabc"))
        self.head = MagicMock()
        self.head.get = AsyncMock(return_value=MagicMock(number=123, hash="0xabc"))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def subnet(self, netuid):
        return MockSubnet(netuid)


def get_mock_neuron(uid: int = 0):
    return Neuron(
        uid=uid,
        hotkey=f"mock_hotkey_{uid}",
        coldkey=f"mock_coldkey_{uid}",
        active=True,
        axon_info=AxonInfo(ip="127.0.0.1", port=8080, protocol=1).model_dump(),
        stake=1.0,
        rank=0.5,
        trust=0.5,
        consensus=0.5,
        incentive=0.5,
        dividends=0.0,
        emission=0.1,
        validator_trust=0.5,
        validator_permit=True,
        last_update=0,
        pruning_score=0,
    )


def get_mock_metagraph(block: int):
    return Metagraph(
        block=block,
        block_hash="0xabc",
        neurons={neuron.hotkey: neuron for neuron in [get_mock_neuron(uid) for uid in range(3)]},
    )
