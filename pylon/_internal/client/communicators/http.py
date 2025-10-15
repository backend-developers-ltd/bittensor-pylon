import logging
from http import HTTPMethod

from httpx import AsyncClient, HTTPStatusError, Request, RequestError, Response

from pylon._internal.client.communicators.abstract import AbstractCommunicator
from pylon._internal.client.config import PylonAsyncClientConfig
from pylon._internal.common.endpoints import Endpoint
from pylon._internal.common.exceptions import PylonRequestException, PylonResponseException
from pylon._internal.common.requests import PylonRequest
from pylon._internal.common.responses import PylonResponse, PylonResponseStatus

logger = logging.getLogger(__name__)


class AsyncHttpCommunicator(AbstractCommunicator[Request, Response]):
    """
    Communicates with Pylon API through HTTP.
    """

    _request_translation = {"set_weights": {"method": HTTPMethod.PUT, "endpoint": Endpoint.SUBNET_WEIGHTS}}

    def __init__(self, config: PylonAsyncClientConfig):
        super().__init__(config)
        self._raw_client: AsyncClient | None = None

    async def open(self) -> None:
        assert self._raw_client is None
        logger.debug(f"Opening client for the server {self.config.address}")
        self._raw_client = AsyncClient(base_url=self.config.address)

    async def close(self) -> None:
        assert self._raw_client is not None
        logger.debug(f"Closing client for the server {self.config.address}")
        await self._raw_client.aclose()
        self._raw_client = None

    async def _translate_request(self, request: PylonRequest) -> Request:
        request_params = self._request_translation[request.rtype]
        return Request(
            method=request_params["method"],
            url=request_params["endpoint"].for_version(request.version),
            json=request.model_dump(),
        )

    async def _translate_response(self, pylon_request: PylonRequest, response: Response) -> PylonResponse:
        return pylon_request.response_cls(status=PylonResponseStatus.SUCCESS, **response.json())

    async def _request(self, request: Request) -> Response:
        assert self._raw_client and not self._raw_client.is_closed, (
            "Client is not open, use context manager or open() method before making a request."
        )
        try:
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

    async def _handle_status_error(self, exc: HTTPStatusError) -> Response:
        raise PylonResponseException("Invalid response from Pylon API.") from exc
