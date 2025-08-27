import asyncio
import tempfile
from dataclasses import asdict
from ipaddress import IPv4Address
from unittest.mock import AsyncMock, MagicMock

import bittensor_wallet
import pytest
from cachetools import TTLCache
from litestar.testing import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from turbobt import Neuron as TurboNeuron
from turbobt.neuron import AxonInfo as TurboAxonInfo
from turbobt.neuron import AxonProtocolEnum

from pylon_common.models import Metagraph, Neuron
from pylon_common.settings import settings
from pylon_service import db
from pylon_service.main import create_app


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
        self.weights.commit = AsyncMock(return_value=123)
        self.commitments = AsyncMock()

    async def get_hyperparameters(self):
        return self._hyperparams.copy()

    async def list_neurons(self, block_hash=None):
        return [get_mock_neuron(uid) for uid in range(3)]


class MockBittensorClient:
    def __init__(self):
        self.wallet = MagicMock()
        self.block = MagicMock()
        self.block.return_value.get = AsyncMock(return_value=MagicMock(number=0, hash="0xabc"))
        self.head = MagicMock()
        self.head.get = AsyncMock(return_value=MagicMock(number=0, hash="0xabc"))
        self._subnets = {}
        self.subnet = MagicMock(side_effect=self._get_subnet)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def _get_subnet(self, netuid):
        if netuid not in self._subnets:
            self._subnets[netuid] = MockSubnet(netuid)
        return self._subnets[netuid]


def get_mock_neuron(uid: int = 0):
    return Neuron.model_validate(asdict(get_mock_turbo_neuron(uid)))


def get_mock_turbo_neuron(uid: int = 0):
    return TurboNeuron(
        subnet=MagicMock(netuid=1),
        uid=uid,
        hotkey=f"mock_hotkey_{uid}",
        coldkey=f"mock_coldkey_{uid}",
        active=True,
        axon_info=TurboAxonInfo(ip=IPv4Address("127.0.0.1"), port=8080, protocol=AxonProtocolEnum.HTTP),
        prometheus_info=MagicMock(),
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


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        db_uri = f"sqlite+aiosqlite:///{temp_dir}/pylon.db"
        monkeypatch.setenv("PYLON_DB_URI", db_uri)
        monkeypatch.setenv("PYLON_DB_DIR", temp_dir)

        new_engine = create_async_engine(db_uri, echo=False, future=True)
        new_session_local = async_sessionmaker(bind=new_engine, class_=AsyncSession, expire_on_commit=False)
        monkeypatch.setattr(db, "engine", new_engine)
        monkeypatch.setattr(db, "SessionLocal", new_session_local)
        yield


@pytest.fixture()
def mock_wallet() -> bittensor_wallet.Wallet:
    wallet = bittensor_wallet.Wallet(
        name=settings.bittensor_wallet_name,
        hotkey=settings.bittensor_wallet_hotkey_name,
    )
    wallet.create_if_non_existent(coldkey_use_password=False, hotkey_use_password=False)
    return wallet


@pytest.fixture
def test_client(monkeypatch):
    monkeypatch.setenv("AM_I_A_VALIDATOR", "True")

    test_app = create_app(tasks=[])
    with TestClient(test_app) as test_client:
        test_client.app.state.bittensor_client = MockBittensorClient()
        test_client.app.state.archive_bittensor_client = MockBittensorClient()
        test_client.app.state.latest_block = None
        test_client.app.state.reveal_round = None
        test_client.app.state.last_commit_block = 0
        test_client.app.state.metagraph_cache = TTLCache(
            maxsize=settings.metagraph_cache_maxsize, ttl=settings.metagraph_cache_ttl
        )
        test_client.app.state.current_epoch_start = 0
        test_client.app.state.hyperparams = {}

        # Initialize task-related state
        test_client.app.state._stop_event = asyncio.Event()
        test_client.app.state._background_tasks = []
        yield test_client
