import logging
from functools import singledispatchmethod
from http import HTTPMethod

from httpx import AsyncClient, HTTPStatusError, Request, RequestError, Response

from pylon._internal.client.communicators.abstract import AbstractCommunicator
from pylon._internal.client.config import AsyncPylonClientConfig
from pylon._internal.common.endpoints import Endpoint
from pylon._internal.common.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.common.requests import GetMetagraphRequest, PylonRequest, SetWeightsRequest
from pylon._internal.common.responses import PylonResponse

logger = logging.getLogger(__name__)


class AsyncHttpCommunicator(AbstractCommunicator[Request, Response]):
    """
    Communicates with Pylon API through HTTP.
    """

    def __init__(self, config: AsyncPylonClientConfig):
        super().__init__(config)
        self._raw_client: AsyncClient | None = None

    async def open(self) -> None:
        assert self._raw_client is None
        logger.debug(f"Opening communicator for the server {self.config.address}")
        self._raw_client = AsyncClient(base_url=self.config.address)

    async def close(self) -> None:
        assert self._raw_client is not None
        logger.debug(f"Closing communicator for the server {self.config.address}")
        await self._raw_client.aclose()
        self._raw_client = None

    @singledispatchmethod
    async def _translate_request(self, request: PylonRequest) -> Request:
        raise NotImplementedError(f"Request of type {type(request).__name__} is not supported.")

    @_translate_request.register
    async def _(self, request: SetWeightsRequest) -> Request:
        return self._raw_client.build_request(
            method=HTTPMethod.PUT,
            url=Endpoint.SUBNET_WEIGHTS.for_version(request.version),
            json=request.model_dump(),
        )

    @_translate_request.register
    async def _(self, request: GetMetagraphRequest) -> Request:
        return self._raw_client.build_request(
            method=HTTPMethod.GET,
            url=Endpoint.METAGRAPH.for_version(request.version),
            params=request.model_dump(exclude_none=True),
        )

    async def _translate_response(self, pylon_request: PylonRequest, response: Response) -> PylonResponse:
        return pylon_request.response_cls(**response.json())

    async def _request(self, request: Request) -> Response:
        assert self._raw_client and not self._raw_client.is_closed, (
            "Communicator is not open, use context manager or open() method before making a request."
        )
        try:
            logger.debug(f"Performing request to {request.url}")
            response = await self._raw_client.send(request)
        except RequestError as e:
            return await self._handle_request_error(e)
        try:
            response.raise_for_status()
        except HTTPStatusError as e:
            return await self._handle_status_error(e)
        return response

    async def _handle_request_error(self, exc: RequestError) -> Response:
        raise PylonRequestException("An error occurred while making a request to Pylon API.") from exc

    # TODO: Add more info about error response to the exception.
    async def _handle_status_error(self, exc: HTTPStatusError) -> Response:
        raise PylonResponseException("Invalid response from Pylon API.") from exc
