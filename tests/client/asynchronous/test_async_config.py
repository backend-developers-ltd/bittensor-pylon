import pytest
from httpx import ConnectTimeout, Response, codes
from tenacity import stop_after_attempt

from pylon._internal.client.asynchronous import AsyncPylonClient
from pylon._internal.client.config import DEFAULT_RETRIES, AsyncPylonClientConfig
from pylon._internal.common.requests import SetWeightsRequest
from pylon._internal.common.responses import PylonResponseStatus


@pytest.mark.parametrize(
    "retries",
    (
        pytest.param(2, id="two_attempts"),
        pytest.param(4, id="four_attempts"),
    ),
)
@pytest.mark.asyncio
async def test_async_config_retries(service_mock, test_url, retries):
    service_mock.put("/api/v1/subnet/weights").mock(
        side_effect=[
            *(ConnectTimeout("Connection timed out") for i in range(retries - 1)),
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
        AsyncPylonClientConfig(address=test_url, retry=DEFAULT_RETRIES.copy(stop=stop_after_attempt(retries)))
    ) as async_client:
        response = await async_client.request(SetWeightsRequest(weights={"h2": 0.1}))
    assert response.status == PylonResponseStatus.SUCCESS
