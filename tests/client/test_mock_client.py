import pytest

from pylon._internal.client.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.client.mock import AsyncMockClient, RaiseRequestError, RaiseResponseError, WorkNormally
from pylon._internal.common.requests import SetWeightsRequest
from pylon._internal.common.responses import SetWeightsResponse
from pylon._internal.common.types import Hotkey, Weight


@pytest.mark.asyncio
async def test_mock_async_pylon_client():
    normal_response = SetWeightsResponse()
    client = AsyncMockClient(
        behavior=[
            RaiseRequestError("Test request error!"),
            RaiseResponseError("Test http status error!"),
            WorkNormally(normal_response),
        ]
    )
    pylon_request = SetWeightsRequest(weights={Hotkey("h1"): Weight(1), Hotkey("h2"): Weight(0.5)})
    with pytest.raises(PylonRequestException, match="Test request error!"):
        await client.request(pylon_request)
    with pytest.raises(PylonResponseException, match="Test http status error!"):
        await client.request(pylon_request)
    response = await client.request(pylon_request)
    assert response == normal_response
    # Check if the client will do the last behavior from the list after it ends.
    response = await client.request(pylon_request)
    assert response == normal_response
    # Check "requests" made.
    assert client.requests_made == [SetWeightsRequest(weights={Hotkey("h1"): Weight(1), Hotkey("h2"): Weight(0.5)})] * 4
