import logging
from abc import ABC
from typing import Generic, TypeVar

from pylon._internal.client.communicators.abstract import AbstractCommunicator
from pylon._internal.client.config import AsyncPylonClientConfig
from pylon._internal.common.requests import PylonRequest
from pylon._internal.common.responses import PylonResponse

C = TypeVar("C", bound=AbstractCommunicator)

logger = logging.getLogger(__name__)


class AbstractAsyncPylonClient(Generic[C], ABC):
    """
    Base for every async Pylon client.

    Pylon client allows easy communication with Pylon service through the use of PylonRequest objects.
    To make a request, use client's `request` method, providing an object of PylonRequest subclass:

    ```
    response = await client.request(GetMetagraphRequest(BlockNumber(1234)))
    ```

    Async pylon client is configured via passed AsyncPylonClientConfig instance.
    """

    _communicator_cls: type[C]

    def __init__(self, config: AsyncPylonClientConfig):
        self.config = config
        self._communicator: C | None = None

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def open(self) -> None:
        """
        Prepares the client to work by opening a communicator.
        """
        assert self._communicator is None
        logger.debug(f"Opening client for the server {self.config.address}")
        self._communicator = self._communicator_cls(self.config)
        await self._communicator.open()

    async def close(self) -> None:
        """
        Closes the communicator.
        """
        assert self._communicator is not None
        logger.debug(f"Closing client for the server {self.config.address}")
        await self._communicator.close()
        self._communicator = None

    async def request(self, request: PylonRequest) -> PylonResponse:
        """
        Entrypoint to the Pylon.

        Makes a request to the Pylon api based on a passed PylonRequest.
        Retries on failures based on a retry config.

        Raises:
            PylonRequestException: If pylon client fails to communicate with the Pylon service after all retry attempts.
            PylonResponseException: If pylon client receives error response from the Pylon service.
        """
        assert self._communicator is not None, (
            "Client is not open, use context manager or the open() method before making a request."
        )
        return await self._communicator.request(request)
