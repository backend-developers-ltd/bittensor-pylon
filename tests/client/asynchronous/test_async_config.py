import pytest
from httpx import ConnectTimeout, Response, codes
from tenacity import stop_after_attempt

from pylon._internal.client.asynchronous import AsyncPylonClient
from pylon._internal.client.config import DEFAULT_RETRIES, AsyncPylonClientConfig
from pylon._internal.common.exceptions import PylonRequestException
from pylon._internal.common.requests import SetWeightsRequest
from pylon._internal.common.responses import SetWeightsResponse
from pylon._internal.common.types import Hotkey, Weight


@pytest.mark.parametrize(
    "attempts",
    (
        pytest.param(2, id="two_attempts"),
        pytest.param(4, id="four_attempts"),
    ),
)
@pytest.mark.asyncio
async def test_async_config_retries_success(service_mock, test_url, attempts):
    route = service_mock.put("/api/v1/weights")
    route.mock(
        side_effect=[
            *(ConnectTimeout("Connection timed out") for i in range(attempts - 1)),
            Response(
                status_code=codes.OK,
                json={
                    "detail": "weights update scheduled",
                    "count": 1,
                },
            ),
        ]
    )
    async with AsyncPylonClient(
        AsyncPylonClientConfig(address=test_url, retry=DEFAULT_RETRIES.copy(stop=stop_after_attempt(attempts)))
    ) as async_client:
        response = await async_client.request(SetWeightsRequest(weights={Hotkey("h2"): Weight(0.1)}))
    assert response == SetWeightsResponse()
    assert route.call_count == attempts


@pytest.mark.asyncio
async def test_async_config_retries_error(service_mock, test_url):
    route = service_mock.put("/api/v1/weights")
    route.mock(side_effect=ConnectTimeout("Connection timed out"))
    async with AsyncPylonClient(
        AsyncPylonClientConfig(
            address=test_url,
            # Check if reraise will be forced to True.
            retry=DEFAULT_RETRIES.copy(stop=stop_after_attempt(2), reraise=False),
        )
    ) as async_client:
        with pytest.raises(PylonRequestException):
            await async_client.request(SetWeightsRequest(weights={Hotkey("h2"): Weight(0.1)}))
    assert route.call_count == 2
