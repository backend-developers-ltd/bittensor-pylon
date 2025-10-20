"""
Tests for the PUT /subnet/weights endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from litestar.testing import AsyncTestClient

from pylon._internal.common.settings import settings
from pylon.service.bittensor.models import Block, BlockHash, RevealRound, SubnetHyperparams
from pylon.service.tasks import ApplyWeights
from tests.helpers import wait_for_background_tasks
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_put_weights_commit_reveal_enabled(test_client: AsyncTestClient, mock_bt_client: MockBittensorClient):
    """
    Test setting weights when commit-reveal is enabled.
    """
    weights = {
        "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty": 0.5,
        "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": 0.3,
        "5CiPPseXPECbkjWCa6MnjNokrgYjMqmKndv2rSnekmSK2DjL": 0.2,
    }

    # Set up behaviors that will persist for the background task
    # The background task calls get_latest_block twice (start and during apply)
    async with mock_bt_client.mock_behavior(
        get_latest_block=[
            Block(number=1000, hash=BlockHash("0xabc123")),  # First call in run_job
            Block(number=1001, hash=BlockHash("0xabc124")),  # Second call in run_job
        ],
        _get_hyperparams=[SubnetHyperparams(commit_reveal_weights_enabled=True)],
        commit_weights=[RevealRound(1005)],
    ):
        response = await test_client.put(
            "/api/v1/subnet/weights",
            json={"weights": weights},
        )

        assert response.status_code == HTTP_200_OK, response.json()
        assert response.json() == {
            "detail": "weights update scheduled",
            "count": 3,
        }

        # Wait for the background task to complete
        await wait_for_background_tasks([ApplyWeights.JOB_NAME])

    # Verify the commit_weights was called with correct arguments
    assert mock_bt_client.calls["commit_weights"] == [
        (settings.bittensor_netuid, weights),
    ]


@pytest.mark.asyncio
async def test_put_weights_commit_reveal_disabled(test_client: AsyncTestClient, mock_bt_client: MockBittensorClient):
    """
    Test setting weights when commit-reveal is disabled.
    """
    weights = {
        "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty": 0.7,
        "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": 0.3,
    }

    # Set up behaviors that will persist for the background task
    async with mock_bt_client.mock_behavior(
        get_latest_block=[
            Block(number=2000, hash=BlockHash("0xdef456")),  # First call in run_job
            Block(number=2000, hash=BlockHash("0xdef456")),  # Second call in run_job
        ],
        _get_hyperparams=[SubnetHyperparams(commit_reveal_weights_enabled=False)],
        set_weights=[None],
    ):
        response = await test_client.put(
            "/api/v1/subnet/weights",
            json={"weights": weights},
        )

        assert response.status_code == HTTP_200_OK, response.json()
        assert response.json() == {
            "detail": "weights update scheduled",
            "count": 2,
        }

        # Wait for the background task to complete
        await wait_for_background_tasks([ApplyWeights.JOB_NAME])

    # Verify set_weights was called with correct arguments
    assert mock_bt_client.calls["set_weights"] == [
        (settings.bittensor_netuid, weights),
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
            {"weights": {"5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty": "invalid"}},
            [
                {
                    "message": "Input should be a valid number, unable to parse string as a number",
                    "key": "weights.5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
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
        "/api/v1/subnet/weights",
        json=json_data,
    )

    assert response.status_code == HTTP_400_BAD_REQUEST, response.json()
    assert response.json() == {
        "status_code": 400,
        "detail": "Validation failed for PUT /api/v1/subnet/weights",
        "extra": expected_extra,
    }
