from abc import ABC, abstractmethod

from httpx import HTTPStatusError, Request, RequestError, Response, codes

from pylon._internal.client.abstract import AbstractAsyncPylonClient
from pylon._internal.common.apiver import ApiVersion
from pylon._internal.common.exceptions import PylonHttpStatusException, PylonRequestException
from pylon._internal.common.models import PylonRequest


class MockAsyncPylonClient(AbstractAsyncPylonClient):
    api_version = ApiVersion.V1

    def __init__(self, behavior: list["Behavior"] | None = None):
        super().__init__("http://testserver")
        self.last_behavior = None
        self.behavior = behavior or [WorkNormally]
        self.requests_made = []

    async def open(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def request(self, request: PylonRequest) -> Response:
        if self.behavior:
            self.last_behavior = self.behavior.pop(0)
        return await self.last_behavior(self, request)

    async def _handle_request_error(self, exc: RequestError) -> None:
        pass

    async def _handle_status_error(self, exc: HTTPStatusError) -> None:
        pass


class Behavior(ABC):
    @abstractmethod
    async def __call__(self, api_client: MockAsyncPylonClient, request: PylonRequest): ...

    @staticmethod
    def httpx_request(pylon_request: PylonRequest) -> Request:
        request_kwargs = pylon_request.request_args()
        # These fields are used in httpx 'send' method, not in a Request itself.
        for arg in ("auth", "follow_redirects"):
            if arg in request_kwargs:
                del request_kwargs[arg]
        return Request(**request_kwargs)


class WorkNormally(Behavior):
    async def __call__(self, api_client: MockAsyncPylonClient, request: PylonRequest):
        api_client.requests_made.append(request.request_args())
        return Response(codes.OK)


class RaiseRequestError(Behavior):
    def __init__(self, msg: str):
        self.msg = msg

    async def __call__(self, api_client: MockAsyncPylonClient, request: PylonRequest):
        api_client.requests_made.append(request.request_args())
        raise PylonRequestException(self.msg, request=self.httpx_request(request))


class RaiseHttpStatusError(Behavior):
    def __init__(self, msg: str, response: Response):
        self.msg = msg
        self.response = response

    async def __call__(self, api_client: MockAsyncPylonClient, request: PylonRequest):
        api_client.requests_made.append(request.request_args())
        raise PylonHttpStatusException(
            self.msg,
            status=self.response.status_code,
            request=self.httpx_request(request),
            response=self.response,
        )
