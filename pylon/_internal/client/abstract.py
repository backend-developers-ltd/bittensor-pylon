from abc import ABC, abstractmethod

from httpx import AsyncClient, HTTPStatusError, RequestError, Response
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from pylon._internal.common.apiver import ApiVersion
from pylon._internal.common.exceptions import PylonRequestException
from pylon._internal.common.models import PylonRequest


class AbstractAsyncPylonClient(ABC):
    api_version: ApiVersion

    def __init__(self, address: str, raw_client_config: dict = None, retry: AsyncRetrying | None = None):
        self.raw_client: AsyncClient | None = None
        self.raw_client_config = raw_client_config or {}
        self.address = address
        self.retry = retry or AsyncRetrying(
            wait=wait_exponential_jitter(initial=0.1, jitter=0.2),
            stop=stop_after_attempt(3),
            retry=retry_if_exception_type(PylonRequestException),
        )
        self.retry.reraise = True

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abstractmethod
    async def open(self) -> None:
        """
        Prepares the client to work. Sets all the fields necessary for the client to work like
        `raw_client`.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Cleans up connections etc...
        """

    @abstractmethod
    async def _handle_request_error(self, exc: RequestError) -> None:
        """
        Handles httpx request error by throwing appropriate pylon client exception.
        """

    @abstractmethod
    async def _handle_status_error(self, exc: HTTPStatusError) -> None:
        """
        Handles httpx status error raised on every non 2XX request by throwing the appropriate pylon
        client exception. May return None in case erroneous response should be returned anyway.
        """

    async def _request(self, *args, **kwargs):
        assert self.raw_client and not self.raw_client.is_closed, (
            "Client is not open, use context manager or open() method."
        )
        async for attempt in self.retry.copy():
            with attempt:
                try:
                    response = await self.raw_client.request(*args, **kwargs)
                except RequestError as e:
                    await self._handle_request_error(e)
                    # _handle_request_error should throw its own error, this is just a safeguard.
                    raise e
                try:
                    response.raise_for_status()
                except HTTPStatusError as e:
                    await self._handle_status_error(e)
        return response

    @abstractmethod
    async def request(self, request: PylonRequest) -> Response:
        """
        Makes a request to the HTTP Pylon api based on a passed PylonRequest subclass.
        """
