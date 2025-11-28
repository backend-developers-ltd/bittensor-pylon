"""
Tests for the PUT /subnet/weights endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import Block, CommitReveal, SubnetHyperparams
from pylon._internal.common.types import BlockHash, BlockNumber, RevealRound
from pylon.service.tasks import ApplyWeights
from tests.helpers import wait_for_background_tasks
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_put_weights_commit_reveal_enabled(test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient):
    """
    Test setting weights when commit-reveal is enabled.
    """
    weights = {
        "hotkey1": 0.5,
        "hotkey2": 0.3,
        "hotkey3": 0.2,
    }

    # Set up behaviors that will persist for the background task
    # The background task calls get_latest_block twice (start and during apply)
    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[
            Block(number=BlockNumber(1000), hash=BlockHash("0xabc123")),  # First call in run_job
            Block(number=BlockNumber(1001), hash=BlockHash("0xabc124")),  # Second call in run_job
        ],
        get_hyperparams=[SubnetHyperparams(commit_reveal_weights_enabled=CommitReveal.V4)],
        commit_weights=[RevealRound(1005)],
    ):
        response = await test_client.put(
            "/api/v1/identity/sn1/subnet/1/weights",
            json={"weights": weights},
        )

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == {
            "detail": "weights update scheduled",
            "count": 3,
        }

        # Wait for the background task to complete
        await wait_for_background_tasks(ApplyWeights.tasks_running)

    # Verify the commit_weights was called with correct arguments
    assert sn1_mock_bt_client.calls["commit_weights"] == [
        (1, weights),
    ]


@pytest.mark.asyncio
async def test_put_weights_commit_reveal_disabled(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient
):
    """
    Test setting weights when commit-reveal is disabled.
    """
    weights = {
        "hotkey1": 0.7,
        "hotkey2": 0.3,
    }

    # Set up behaviors that will persist for the background task
    async with sn2_mock_bt_client.mock_behavior(
        get_latest_block=[
            Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),  # First call in run_job
            Block(number=BlockNumber(2000), hash=BlockHash("0xdef456")),  # Second call in run_job
        ],
        get_hyperparams=[SubnetHyperparams(commit_reveal_weights_enabled=CommitReveal.DISABLED)],
        set_weights=[None],
    ):
        response = await test_client.put(
            "/api/v1/identity/sn2/subnet/2/weights",
            json={"weights": weights},
        )

        assert response.status_code == HTTP_200_OK, response.content
        assert response.json() == {
            "detail": "weights update scheduled",
            "count": 2,
        }

        # Wait for the background task to complete
        await wait_for_background_tasks(ApplyWeights.tasks_running)

    # Verify set_weights was called with correct arguments
    assert sn2_mock_bt_client.calls["set_weights"] == [
        (2, weights),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "json_data,expected_extra",
    [
        pytest.param(
            {},
            [{"message": "Field required", "key": "weights"}],
            id="missing_weights_field",
        ),
        pytest.param(
            {"weights": {}},
            [{"message": "Value error, No weights provided", "key": "weights"}],
            id="empty_weights",
        ),
        pytest.param(
            {"weights": {"hotkey1": "invalid"}},
            [
                {
                    "message": "Input should be a valid number, unable to parse string as a number",
                    "key": "weights.hotkey1",
                }
            ],
            id="invalid_weight_value",
        ),
        pytest.param(
            {"weights": {"": 0.5}},
            [{"message": "Value error, Invalid hotkey: '' must be a non-empty string", "key": "weights"}],
            id="empty_hotkey",
        ),
    ],
)
async def test_put_weights_validation_errors(test_client: AsyncTestClient, json_data: dict, expected_extra: list):
    """
    Test that invalid weight data fails validation.
    """
    response = await test_client.put(
        "/api/v1/identity/sn1/subnet/1/weights",
        json=json_data,
    )

    assert response.status_code == HTTP_400_BAD_REQUEST, response.content
    assert response.json() == {
        "status_code": 400,
        "detail": "Validation failed for PUT /api/v1/identity/sn1/subnet/1/weights",
        "extra": expected_extra,
    }
