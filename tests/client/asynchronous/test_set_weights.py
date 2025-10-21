import json

import pytest
from httpx import ConnectTimeout, Response, codes

from pylon._internal.common.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.common.requests import SetWeightsRequest
from pylon._internal.common.responses import PylonResponseStatus, SetWeightsResponse


@pytest.mark.asyncio
async def test_async_client_set_weights_success(async_client, service_mock):
    route = service_mock.put("/api/v1/subnet/weights")
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
        response = await async_client.request(SetWeightsRequest(weights={"h1": 0.2}))
    assert response == SetWeightsResponse(status=PylonResponseStatus.SUCCESS)
    assert json.loads(route.calls.last.request.content) == {"weights": {"h1": 0.2}}


@pytest.mark.asyncio
async def test_async_client_set_weights_retries_success(async_client, service_mock):
    service_mock.put("/api/v1/subnet/weights").mock(
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
        response = await async_client.request(SetWeightsRequest(weights={"h2": 0.1}))
    assert response == SetWeightsResponse(status=PylonResponseStatus.SUCCESS)


@pytest.mark.asyncio
async def test_async_client_set_weights_request_error(async_client, service_mock):
    assert async_client.config.retry.stop.max_attempt_number == 3
    service_mock.put("/api/v1/subnet/weights").mock(
        side_effect=[
            ConnectTimeout("Connection timed out"),
        ]
        * 3
    )
    async with async_client:
        with pytest.raises(PylonRequestException, match="An error occurred while making a request to Pylon API."):
            await async_client.request(SetWeightsRequest(weights={"h2": 0.1}))


@pytest.mark.asyncio
async def test_async_client_set_weights_response_error(async_client, service_mock):
    service_mock.put("/api/v1/subnet/weights").mock(return_value=Response(status_code=codes.INTERNAL_SERVER_ERROR))
    async with async_client:
        with pytest.raises(PylonResponseException, match="Invalid response from Pylon API."):
            await async_client.request(SetWeightsRequest(weights={"h2": 0.1}))
