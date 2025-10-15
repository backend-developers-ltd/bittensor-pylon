from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pylon._internal.client.config import PylonAsyncClientConfig
from pylon._internal.common.requests import PylonRequest
from pylon._internal.common.responses import PylonResponse

RawRequest = TypeVar("RawRequest")
RawResponse = TypeVar("RawResponse")


class AbstractCommunicator(Generic[RawRequest, RawResponse], ABC):
    """
    Base for every communicator class.

    Communicators are objects that Pylon client uses to communicate with Pylon API. It translates between the client
    interface and the Pylon API interface, for example, changing an http response object into a PylonResponse object.
    """

    def __init__(self, config: PylonAsyncClientConfig):
        self.config = config

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abstractmethod
    async def open(self) -> None:
        """
        Prepares the communicator to work. Sets all the fields necessary for the client to work,
        for example, an http client.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Cleans up connections etc...
        """

    @abstractmethod
    async def _request(self, request: RawRequest) -> RawResponse:
        """
        Makes a raw response out of a raw request by communicating with Pylon.
        """

    @abstractmethod
    async def _translate_request(self, request: PylonRequest) -> RawRequest:
        """
        Translates PylonRequest into a raw request object that will be used to communicate with Pylon.
        """

    @abstractmethod
    async def _translate_response(self, pylon_request: PylonRequest, response: RawResponse) -> PylonResponse:
        """
        Translates the outcome of the _request method (raw response object) into a PylonResponse instance.
        """

    async def request(self, request: PylonRequest) -> PylonResponse:
        """
        Entrypoint to the Pylon API.

        Makes a request to the Pylon API based on a passed PylonRequest. Retries on failures based on a retry
        config.
        Returns a response translated into a PylonResponse instance.
        """
        raw_request = await self._translate_request(request)
        async for attempt in self.config.retry.copy():
            with attempt:
                raw_response = await self._request(raw_request)
        return await self._translate_response(request, raw_response)
