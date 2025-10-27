from abc import ABC, abstractmethod

from pylon._internal.client.abstract import AbstractAsyncPylonClient
from pylon._internal.client.communicators.mock import MockCommunicator
from pylon._internal.client.config import AsyncPylonClientConfig
from pylon._internal.client.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.common.requests import PylonRequest
from pylon._internal.common.responses import PylonResponse


class AsyncMockClient(AbstractAsyncPylonClient):
    _communicator_cls = MockCommunicator

    def __init__(self, behavior: list["Behavior"] | None = None):
        super().__init__(AsyncPylonClientConfig(address="http://testserver"))
        self.last_behavior = None
        self.behavior = behavior or [WorkNormally(PylonResponse())]
        self.requests_made = []

    async def open(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def request(self, request: PylonRequest) -> PylonResponse:
        if self.behavior:
            self.last_behavior = self.behavior.pop(0)
        assert self.last_behavior is not None
        return await self.last_behavior(self, request)


class Behavior(ABC):
    @abstractmethod
    async def __call__(self, api_client: AsyncMockClient, request: PylonRequest) -> PylonResponse: ...


class WorkNormally(Behavior):
    def __init__(self, response: PylonResponse):
        self.response = response

    async def __call__(self, api_client: AsyncMockClient, request: PylonRequest) -> PylonResponse:
        api_client.requests_made.append(request)
        return self.response


class RaiseRequestError(Behavior):
    def __init__(self, msg: str):
        self.msg = msg

    async def __call__(self, api_client: AsyncMockClient, request: PylonRequest) -> PylonResponse:
        api_client.requests_made.append(request)
        raise PylonRequestException(self.msg)


class RaiseResponseError(Behavior):
    def __init__(self, msg: str):
        self.msg = msg

    async def __call__(self, api_client: AsyncMockClient, request: PylonRequest) -> PylonResponse:
        api_client.requests_made.append(request)
        raise PylonResponseException(self.msg)
