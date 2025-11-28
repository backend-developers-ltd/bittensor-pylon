import pytest
from bittensor_wallet import Wallet
from polyfactory.pytest_plugin import register_fixture

from tests.factories import BlockFactory, NeuronFactory


@pytest.fixture
def wallet():
    return Wallet(path="tests/wallets", name="pylon", hotkey="pylon")


register_fixture(BlockFactory)
register_fixture(NeuronFactory)
