import logging
from typing import Any, cast

import httpx
from httpx import AsyncClient, Limits, Timeout, TransportError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pylon_service.constants import (
    ENDPOINT_BLOCK_HASH,
    ENDPOINT_COMMITMENT,
    ENDPOINT_COMMITMENTS,
    ENDPOINT_EPOCH,
    ENDPOINT_FORCE_COMMIT_WEIGHTS,
    ENDPOINT_HYPERPARAMS,
    ENDPOINT_LATEST_BLOCK,
    ENDPOINT_LATEST_METAGRAPH,
    ENDPOINT_LATEST_WEIGHTS,
    ENDPOINT_SET_COMMITMENT,
    ENDPOINT_SET_HYPERPARAM,
    ENDPOINT_SET_WEIGHT,
    ENDPOINT_UPDATE_WEIGHT,
    ENDPOINT_WEIGHTS,
    format_endpoint,
)
from pylon_service.models import Epoch, Metagraph

from .mock import MockHandler

logger = logging.getLogger(__name__)


class PylonClient:
    """An asynchronous client for the bittensor-pylon service."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1",
        port: int = 8000,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        client: AsyncClient | None = None,
        mock_data_path: str | None = None,
    ):
        """Initializes the PylonClient.

        Args:
            base_url: The base URL of the pylon service.
            port: The port of the pylon service.
            timeout: The timeout for requests in seconds.
            max_retries: The maximum number of retries for failed requests.
            backoff_factor: The backoff factor for exponential backoff between retries.
            client: An optional pre-configured httpx.AsyncClient.
            mock_data_path: Path to a JSON file with mock data to run the client in mock mode.
        """
        self.port = port
        self.base_url = f"{base_url}:{self.port}"
        self._timeout = Timeout(timeout)
        self._limits = Limits(max_connections=100, max_keepalive_connections=20)
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client = client
        self._should_close_client = client is None
        self.mock = None
        self.override = None

        if mock_data_path:
            self._setup_mock_client(mock_data_path)

    def _setup_mock_client(self, mock_data_path: str):
        """Configures the client to use a mock transport."""
        mock_handler = MockHandler(mock_data_path, self.base_url)
        transport = httpx.ASGITransport(app=cast(Any, mock_handler.mock_app))
        self._client = AsyncClient(transport=transport, base_url=self.base_url)
        self._should_close_client = True
        self.mock = mock_handler.hooks
        self.override = mock_handler.override

    async def __aenter__(self) -> "PylonClient":
        if self._client is None:
            self._client = AsyncClient(base_url=self.base_url, timeout=self._timeout, limits=self._limits)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client and self._should_close_client:
            await self._client.aclose()

    @property
    def client(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError("Client has not been initialized. Use 'async with PylonClient() as client:' syntax.")
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(TransportError),
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Makes an async HTTP request with error handling and retries."""
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.warning(f"An error occurred while requesting {e.request.url!r}: {e}")
            raise

    async def get_latest_block(self) -> dict | None:
        return await self._request("get", ENDPOINT_LATEST_BLOCK)

    async def get_metagraph(self, block: int | None = None) -> Metagraph | None:
        endpoint = f"/metagraph/{block}" if block else ENDPOINT_LATEST_METAGRAPH
        data = await self._request("get", endpoint)
        return Metagraph(**data) if data else None

    async def get_block_hash(self, block: int) -> dict | None:
        return await self._request("get", format_endpoint(ENDPOINT_BLOCK_HASH, block=block))

    async def get_epoch(self, block: int | None = None) -> Epoch | None:
        endpoint = f"{ENDPOINT_EPOCH}/{block}" if block else ENDPOINT_EPOCH
        data = await self._request("get", endpoint)
        return Epoch(**data) if data else None

    async def get_hyperparams(self) -> dict | None:
        return await self._request("get", ENDPOINT_HYPERPARAMS)

    async def set_hyperparam(self, name: str, value: Any) -> dict | None:
        return await self._request("put", ENDPOINT_SET_HYPERPARAM, json={"name": name, "value": value})

    async def update_weight(self, hotkey: str, weight_delta: float) -> dict | None:
        return await self._request("put", ENDPOINT_UPDATE_WEIGHT, json={"hotkey": hotkey, "weight_delta": weight_delta})

    async def set_weight(self, hotkey: str, weight: float) -> dict | None:
        return await self._request("put", ENDPOINT_SET_WEIGHT, json={"hotkey": hotkey, "weight": weight})

    async def get_weights(self, block: int | None = None) -> dict | None:
        if block is not None:
            endpoint = format_endpoint(ENDPOINT_WEIGHTS, block=block)
        else:
            endpoint = ENDPOINT_LATEST_WEIGHTS
        return await self._request("get", endpoint)

    async def force_commit_weights(self) -> dict | None:
        return await self._request("post", ENDPOINT_FORCE_COMMIT_WEIGHTS)

    async def get_commitment(self, hotkey: str, block: int | None = None) -> dict | None:
        params = {"block": block} if block else {}
        return await self._request("get", format_endpoint(ENDPOINT_COMMITMENT, hotkey=hotkey), params=params)

    async def get_commitments(self, block: int | None = None) -> dict | None:
        params = {"block": block} if block else {}
        return await self._request("get", ENDPOINT_COMMITMENTS, params=params)

    async def set_commitment(self, data_hex: str) -> dict | None:
        return await self._request("post", ENDPOINT_SET_COMMITMENT, json={"data_hex": data_hex})
