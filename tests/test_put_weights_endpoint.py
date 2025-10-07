from __future__ import annotations

import asyncio
from unittest import mock
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from litestar import Litestar
from litestar.testing import TestClient
from turbobt import Block

from pylon_common.settings import settings
from pylon_service.api import put_weights_endpoint
from pylon_service.tasks import ApplyWeights
from pylon_service.utils import get_epoch_containing_block
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


def test_put_weights_endpoint_not_current_tempo(client, token, mock_bittensor_client, wait_for_tasks):
    payload = {"weights": {"mock_hotkey_0": 0.7, "mock_hotkey_1": 0.3, "does_not_matter": 0.2}}

    initial_block_number = settings.tempo
    initial_epoch = get_epoch_containing_block(initial_block_number)
    current_block_number = initial_block_number + 10
    next_epoch_block_number = initial_epoch.end + 1

    mock_bittensor_client.head.get.side_effect = [
        Block(block_number=current_block_number, block_hash="123", client=mock_bittensor_client),
        Block(block_number=next_epoch_block_number, block_hash="345", client=mock_bittensor_client),
    ]
    response = client.put("/subnet/weights", json=payload, headers={"Authorization": f"Bearer {token}"})
    wait_for_tasks([ApplyWeights.JOB_NAME])

    assert response.status_code == 200

    assert len(mock_bittensor_client.head.get.call_args_list) == 2
    assert not mock_bittensor_client.subnet(settings.bittensor_netuid).weights.set.called
    assert not mock_bittensor_client.subnet(settings.bittensor_netuid).weights.commit.called


def test_put_weights_endpoint_retry(client, token, mock_bittensor_client, monkeypatch, wait_for_tasks):
    payload = {"weights": {"mock_hotkey_0": 0.7, "mock_hotkey_1": 0.3, "does_not_matter": 0.2}}

    monkeypatch.setattr(ApplyWeights, "_apply_weights", MagicMock(side_effect=Exception("triggered by test")))

    mock_sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", mock_sleep)
    monkeypatch.setattr(settings, "weights_retry_attempts", 3)

    response = client.put("/subnet/weights", json=payload, headers={"Authorization": f"Bearer {token}"})
    wait_for_tasks([ApplyWeights.JOB_NAME])

    assert response.status_code == 200
    assert mock_sleep.call_args_list == [mock.call(x) for x in [1, 2, 4, 8]]

    assert not mock_bittensor_client.subnet(settings.bittensor_netuid).weights.set.called
    assert not mock_bittensor_client.subnet(settings.bittensor_netuid).weights.commit.called
