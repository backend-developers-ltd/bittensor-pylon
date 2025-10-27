from pylon._internal.client.communicators.abstract import AbstractCommunicator
from pylon._internal.common.requests import PylonRequest
from pylon._internal.common.responses import PylonResponse


class MockCommunicator(AbstractCommunicator[PylonRequest, PylonResponse]):
    async def open(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def _request(self, request: PylonRequest) -> PylonResponse:
        raise NotImplementedError

    async def _translate_request(self, request: PylonRequest) -> PylonRequest:
        raise NotImplementedError

    async def _translate_response(self, pylon_request: PylonRequest, response: PylonResponse) -> PylonResponse:
        raise NotImplementedError
