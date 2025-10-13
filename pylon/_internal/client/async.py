from httpx import AsyncClient, HTTPStatusError, RequestError, Response

from pylon._internal.client.abstract import AbstractAsyncPylonClient
from pylon._internal.common.apiver import ApiVersion
from pylon._internal.common.exceptions import PylonHttpStatusException, PylonRequestException
from pylon._internal.common.models import PylonRequest


class AsyncPylonClient(AbstractAsyncPylonClient):
    api_version = ApiVersion.V1

    async def open(self) -> None:
        assert "base_url" not in self.raw_client_config, (
            "Do not provide 'base_url' in raw_client_config, it is set automatically to the value of address arg."
        )
        self.raw_client = AsyncClient(base_url=self.address, **self.raw_client_config)

    async def close(self) -> None:
        await self.raw_client.aclose()

    async def request(self, request: PylonRequest) -> Response:
        return await self._request(**request.request_args())

    async def _handle_request_error(self, exc: RequestError) -> None:
        raise PylonRequestException(
            "An error occurred while making a request to Pylon API.", request=exc.request
        ) from exc

    async def _handle_status_error(self, exc: HTTPStatusError) -> None:
        raise PylonHttpStatusException(
            "Invalid response from Pylon API.",
            status=exc.response.status_code,
            request=exc.request,
            response=exc.response,
        ) from exc
