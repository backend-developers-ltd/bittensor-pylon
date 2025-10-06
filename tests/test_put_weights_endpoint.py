from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from litestar import Litestar
from litestar.testing import TestClient

from pylon_common.settings import settings
from pylon_service.api import put_weights_endpoint
from pylon_service.tasks import ApplyWeights
from tests.conftest import MockBittensorClient


@pytest.fixture
def client():
    app = Litestar(route_handlers=[put_weights_endpoint])
    with TestClient(app) as client:
        yield client


@pytest.fixture
def token(monkeypatch):
    token_ = "test-token"
    monkeypatch.setattr(settings, "auth_token", token_)
    return token_


@pytest.fixture
def mock_bittensor_client(monkeypatch):
    bt_client = MockBittensorClient()
    monkeypatch.setattr("pylon_service.api.Bittensor", lambda wallet, uri: bt_client)
    return bt_client


@pytest.fixture
def put_weights_client(monkeypatch, client, token):
    monkeypatch.setattr(settings, "bittensor_network", "mock://network")

    dummy_wallet = object()
    monkeypatch.setattr("pylon_service.api.get_bt_wallet", lambda _settings: dummy_wallet)

    mock_bittensor_instance = MagicMock()
    mock_bittensor_class = MagicMock(return_value=mock_bittensor_instance)
    monkeypatch.setattr("pylon_service.api.Bittensor", mock_bittensor_class)

    schedule_mock = AsyncMock()
    monkeypatch.setattr("pylon_service.api.ApplyWeights.schedule", schedule_mock)

    yield client, token, schedule_mock, mock_bittensor_class, mock_bittensor_instance


def test_put_weights_endpoint_success(put_weights_client):
    client, token, schedule_mock, mock_bittensor_class, mock_bittensor_instance = put_weights_client

    payload = {"weights": {"hotkey1": 0.7, "hotkey2": 0.3}}

    response = client.put("/subnet/weights", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"detail": "weights update scheduled", "count": 2}

    mock_bittensor_class.assert_called_once_with(wallet=ANY, uri="mock://network")
    schedule_mock.assert_awaited_once_with(mock_bittensor_instance, payload["weights"])


@pytest.mark.parametrize(
    "headers, expected_detail",
    [
        (
            {"Authorization": "Bearer some invalid token"},
            "Invalid auth token",
        ),
        (
            {},
            "Auth token required",
        ),
    ],
)
def test_put_weights_endpoint_invalid_token(headers, expected_detail, put_weights_client):
    client, _token, schedule_mock, mock_bittensor_class, _mock_bittensor_instance = put_weights_client

    response = client.put("/subnet/weights", json={"weights": {"hotkey": 1.0}}, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": expected_detail}

    mock_bittensor_class.assert_not_called()
    schedule_mock.assert_not_called()


def test_put_weights_endpoint_no_token_configured(put_weights_client, monkeypatch, wait_for_tasks):
    client, _token, schedule_mock, mock_bittensor_class, _mock_bittensor_instance = put_weights_client

    monkeypatch.setattr(settings, "auth_token", "")

    response = client.put(
        "/subnet/weights", json={"weights": {"hotkey": 1.0}}, headers={"Authorization": "Bearer some token"}
    )
    wait_for_tasks([ApplyWeights.JOB_NAME])

    assert response.status_code == 500
    assert response.json() == {"detail": "Token auth not configured"}

    mock_bittensor_class.assert_not_called()
    schedule_mock.assert_not_called()


@pytest.mark.parametrize(
    "hyperparams, method",
    [
        (
            {},
            "set",
        ),
        (
            {"commit_reveal_weights_enabled": True},
            "commit",
        ),
    ],
)
def test_put_weights_endpoint_reveal(hyperparams, method, client, token, mock_bittensor_client, wait_for_tasks):
    mock_bittensor_client.subnet(settings.bittensor_netuid)._hyperparams.update(hyperparams)
    payload = {"weights": {"mock_hotkey_0": 0.7, "mock_hotkey_1": 0.3, "mock_hotkey_321": 0.2}}

    response = client.put("/subnet/weights", json=payload, headers={"Authorization": f"Bearer {token}"})
    wait_for_tasks([ApplyWeights.JOB_NAME])

    assert response.status_code == 200

    getattr(mock_bittensor_client.subnet(settings.bittensor_netuid).weights, method).assert_called_once_with(
        {0: 0.7, 1: 0.3}
    )


def test_put_weights_endpoint_not_current_tempo(client, token, mock_bittensor_client, monkeypatch):
    # WARNING: llm generated
    from pylon_service import tasks
    from pylon_service.utils import get_epoch_containing_block

    payload = {"weights": {"mock_hotkey_0": 0.5, "mock_hotkey_1": 0.5}}

    mock_apply_weights = AsyncMock()
    monkeypatch.setattr(tasks.ApplyWeights, "_apply_weights", mock_apply_weights)

    initial_block = settings.tempo
    initial_epoch = get_epoch_containing_block(initial_block)
    subsequent_block = initial_epoch.end + 1

    class MutableBlock:
        def __init__(self, first: int, second: int):
            self._values = [first, first, second]
            self._index = 0
            self.hash = "0xabc"

        @property
        def number(self):
            idx = self._index if self._index < len(self._values) else len(self._values) - 1
            self._index += 1
            return self._values[idx]

    mutable_block = MutableBlock(initial_block, subsequent_block)

    mock_head = AsyncMock(return_value=mutable_block)
    monkeypatch.setattr(mock_bittensor_client.head, "get", mock_head)

    async def immediate_schedule(cls, client_, weights):
        job = cls(client_)
        await job.run_job(weights)
        return job

    monkeypatch.setattr(tasks.ApplyWeights, "schedule", classmethod(immediate_schedule))

    response = client.put("/subnet/weights", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert mutable_block._index >= 3  # ensure _is_current_tempo accessed updated block number
    mock_apply_weights.assert_not_awaited()

    subnet_weights = mock_bittensor_client.subnet(settings.bittensor_netuid).weights
    subnet_weights.set.assert_not_awaited()
    subnet_weights.commit.assert_not_awaited()


def test_put_weights_endpoint_retry(client, token, mock_bittensor_client, monkeypatch):
    # WARNING: llm generated
    from pylon_service import tasks

    payload = {"weights": {"mock_hotkey_0": 1.0}}

    monkeypatch.setattr(settings, "weights_retry_attempts", 2)
    monkeypatch.setattr(settings, "weights_retry_delay_seconds", 0)

    apply_mock = AsyncMock(side_effect=[RuntimeError("boom"), RuntimeError("boom again"), None])
    monkeypatch.setattr(tasks.ApplyWeights, "_apply_weights", apply_mock)

    sleep_mock = AsyncMock()
    monkeypatch.setattr(tasks.asyncio, "sleep", sleep_mock)

    error_calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
    original_error = tasks.logger.error

    def error_spy(message, *args, **kwargs):
        formatted = message % args if args else message
        error_calls.append((formatted, args, kwargs))
        return original_error(message, *args, **kwargs)

    monkeypatch.setattr(tasks.logger, "error", error_spy)

    latest_block = MagicMock(number=settings.tempo, hash="0xabc")
    monkeypatch.setattr(mock_bittensor_client.head, "get", AsyncMock(return_value=latest_block))

    async def immediate_schedule(cls, client_, weights):
        job = cls(client_)
        await job.run_job(weights)
        return job

    monkeypatch.setattr(tasks.ApplyWeights, "schedule", classmethod(immediate_schedule))

    response = client.put("/subnet/weights", json=payload, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert apply_mock.await_count == 3
    assert sleep_mock.await_count == 2
    assert len(error_calls) == 2
    assert error_calls[0][0].startswith("Error executing apply_weights")
