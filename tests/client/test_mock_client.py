import pytest
from httpx import Response, codes

from pylon._internal.client.mock import MockAsyncPylonClient, RaiseHttpStatusError, RaiseRequestError, WorkNormally
from pylon._internal.common.exceptions import PylonHttpStatusException, PylonRequestException
from pylon._internal.common.models import SetWeightsRequest


@pytest.mark.asyncio
async def test_mock_async_pylon_client():
    client = MockAsyncPylonClient(
        behavior=[
            RaiseRequestError("Test request error!"),
            RaiseHttpStatusError("Test http status error!", Response(codes.BAD_REQUEST)),
            WorkNormally(),
        ]
    )
    pylon_request = SetWeightsRequest(weights={"h1": 1, "h2": 0.5})
    with pytest.raises(PylonRequestException, match="Test request error!"):
        await client.request(pylon_request)
    with pytest.raises(
        PylonHttpStatusException, match="Test http status error!", check=lambda e: e.status == codes.BAD_REQUEST
    ):
        await client.request(pylon_request)
    await client.request(pylon_request)
    # Check if the client will do the last behavior from the list after it ends.
    await client.request(pylon_request)
    # Check "requests" made.
    assert (
        client.requests_made
        == [
            {
                "method": "PUT",
                "url": "/api/v1/subnet/weights",
                "json": {"weights": {"h1": 1.0, "h2": 0.5}},
            }
        ]
        * 4
    )
