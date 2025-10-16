import pytest

from pylon._internal.client.mock import AsyncMockClient, RaiseRequestError, RaiseResponseError, WorkNormally
from pylon._internal.common.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.common.requests import SetWeightsRequest
from pylon._internal.common.responses import PylonResponseStatus, SetWeightsResponse


@pytest.mark.asyncio
async def test_mock_async_pylon_client():
    client = AsyncMockClient(
        behavior=[
            RaiseRequestError("Test request error!"),
            RaiseResponseError("Test http status error!"),
            WorkNormally(SetWeightsResponse(status=PylonResponseStatus.SUCCESS)),
        ]
    )
    pylon_request = SetWeightsRequest(weights={"h1": 1, "h2": 0.5})
    with pytest.raises(PylonRequestException, match="Test request error!"):
        await client.request(pylon_request)
    with pytest.raises(PylonResponseException, match="Test http status error!"):
        await client.request(pylon_request)
    await client.request(pylon_request)
    # Check if the client will do the last behavior from the list after it ends.
    await client.request(pylon_request)
    # Check "requests" made.
    assert client.requests_made == [SetWeightsRequest(weights={"h1": 1, "h2": 0.5})] * 4
