import json

import pytest
from httpx import ConnectTimeout, Response, codes
from pydantic import ValidationError

from pylon._internal.common.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.common.requests import SetWeightsRequest
from pylon._internal.common.responses import SetWeightsResponse
from pylon._internal.common.types import Hotkey, Weight


@pytest.mark.asyncio
async def test_async_client_set_weights_success(async_client, service_mock):
    route = service_mock.put("/api/v1/weights")
    route.mock(
        return_value=Response(
            status_code=codes.OK,
            json={
                "detail": "weights update scheduled",
                "count": 1,
            },
        )
    )
    async with async_client:
        response = await async_client.request(SetWeightsRequest(weights={Hotkey("h1"): Weight(0.2)}))
    assert response == SetWeightsResponse()
    assert json.loads(route.calls.last.request.content) == {"weights": {"h1": 0.2}}


@pytest.mark.asyncio
async def test_async_client_set_weights_retries_success(async_client, service_mock):
    service_mock.put("/api/v1/weights").mock(
        side_effect=[
            ConnectTimeout("Connection timed out"),
            ConnectTimeout("Connection timed out"),
            Response(
                status_code=codes.OK,
                json={
                    "detail": "weights update scheduled",
                    "count": 1,
                },
            ),
        ]
    )
    async with async_client:
        response = await async_client.request(SetWeightsRequest(weights={Hotkey("h2"): Weight(0.1)}))
    assert response == SetWeightsResponse()


@pytest.mark.asyncio
async def test_async_client_set_weights_request_error(async_client, service_mock):
    assert async_client.config.retry.stop.max_attempt_number <= 3  # Don't let the tests grow slow.
    service_mock.put("/api/v1/weights").mock(
        side_effect=ConnectTimeout("Connection timed out"),
    )
    async with async_client:
        with pytest.raises(PylonRequestException, match="An error occurred while making a request to Pylon API."):
            await async_client.request(SetWeightsRequest(weights={Hotkey("h2"): Weight(0.1)}))


@pytest.mark.asyncio
async def test_async_client_set_weights_response_error(async_client, service_mock):
    service_mock.put("/api/v1/weights").mock(return_value=Response(status_code=codes.INTERNAL_SERVER_ERROR))
    async with async_client:
        with pytest.raises(PylonResponseException, match="Invalid response from Pylon API."):
            await async_client.request(SetWeightsRequest(weights={Hotkey("h2"): Weight(0.1)}))


@pytest.mark.parametrize(
    "invalid_weights,expected_errors",
    [
        pytest.param(
            {},
            [{"type": "value_error", "loc": ("weights",), "msg": "Value error, No weights provided"}],
            id="empty_weights",
        ),
        pytest.param(
            {"": 0.5},
            [
                {
                    "type": "value_error",
                    "loc": ("weights",),
                    "msg": "Value error, Invalid hotkey: '' must be a non-empty string",
                }
            ],
            id="empty_hotkey",
        ),
        pytest.param(
            {"hotkey1": "invalid"},
            [
                {
                    "type": "float_parsing",
                    "loc": ("weights", "hotkey1"),
                    "msg": "Input should be a valid number, unable to parse string as a number",
                }
            ],
            id="non_numeric_weight",
        ),
        pytest.param(
            {"hotkey1": [0.5]},
            [{"type": "float_type", "loc": ("weights", "hotkey1"), "msg": "Input should be a valid number"}],
            id="list_weight",
        ),
    ],
)
def test_set_weights_request_validation_error(invalid_weights, expected_errors):
    """
    Test that SetWeightsRequest validates input correctly.
    """
    with pytest.raises(ValidationError) as exc_info:
        SetWeightsRequest(weights=invalid_weights)

    errors = exc_info.value.errors(include_url=False, include_context=False, include_input=False)
    assert errors == expected_errors
