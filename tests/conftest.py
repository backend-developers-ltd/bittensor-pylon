import pytest
from bittensor_wallet import Wallet


@pytest.fixture
def wallet():
    return Wallet(path="tests/wallets", name="pylon", hotkey="pylon")
