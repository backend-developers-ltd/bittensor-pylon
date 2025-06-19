import asyncio
import logging
from typing import Any

import docker
import httpx
from httpx import AsyncClient, Limits, Timeout, TransportError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.models import Epoch, Metagraph

logger = logging.getLogger(__name__)

# API endpoint paths
ENDPOINT_LATEST_BLOCK = "/latest_block"
ENDPOINT_METAGRAPH = "/metagraph"
ENDPOINT_BLOCK_HASH = "/block_hash/{block_number}"
ENDPOINT_EPOCH = "/epoch"

ENDPOINT_HYPERPARAMS = "/hyperparams"
ENDPOINT_SET_HYPERPARAM = "/set_hyperparam"

ENDPOINT_UPDATE_WEIGHT = "/update_weight"
ENDPOINT_SET_WEIGHT = "/set_weight"
ENDPOINT_RAW_WEIGHTS = "/raw_weights"
ENDPOINT_FORCE_COMMIT_WEIGHTS = "/force_commit_weights"

ENDPOINT_GET_COMMITMENT = "/get_commitment/{hotkey}"
ENDPOINT_GET_COMMITMENTS = "/get_commitments"
ENDPOINT_SET_COMMITMENT = "/set_commitment"


class PylonClient:
    """An asynchronous client for the bittensor-pylon service."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1",
        port: int = 8000,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        """Initializes the PylonClient.

        Args:
            base_url: The base URL of the pylon service.
            port: The port of the pylon service.
            timeout: The timeout for requests in seconds.
            max_retries: The maximum number of retries for failed requests.
            backoff_factor: The backoff factor for exponential backoff between retries.
        """
        self.port = port  # keep for docker mapping
        self.base_url = f"{base_url}:{self.port}"
        self._timeout = Timeout(timeout)
        self._limits = Limits(max_connections=100, max_keepalive_connections=20)
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client: AsyncClient | None = None

        self._managed_container = None

    async def __aenter__(self) -> "PylonClient":
        self._client = AsyncClient(base_url=self.base_url, timeout=self._timeout, limits=self._limits)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError("Client has not been initialized. Use 'async with PylonClient() as client:' syntax.")
        return self._client

    async def start_pylon_service(
        self,
        env_vars: dict,
        image_name: str = "bittensor-pylon",
        timeout: float = 10.0,
    ):
        docker_client = docker.from_env()
        container = docker_client.containers.run(
            image_name,
            detach=True,
            ports={"8000/tcp": self.port},
            volumes={env_vars["pylon_db_path"]: {"bind": "/app/pylon.db", "mode": "rw"}},
            environment=env_vars,
        )
        await asyncio.wait_for(self._wait_for_pylon_service(), timeout=timeout)
        logger.info(f"Pylon container {container.short_id} started.")
        return container

    async def stop_pylon_service(self, container: docker.models.containers.Container):
        container.stop()
        container.remove()
        logger.info("Pylon container stopped and removed.")

    async def _wait_for_pylon_service(self):
        await asyncio.sleep(1)
        while not await self._check_pylon_service():
            await asyncio.sleep(1)

    async def _check_pylon_service(self):
        try:
            await self.get_latest_block()
        except Exception as e:
            logger.error(f"Pylon service check failed: {e}")
            return False
        return True

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

    async def get_metagraph(self, block_number: int | None = None) -> Metagraph | None:
        endpoint = f"{ENDPOINT_METAGRAPH}/{block_number}" if block_number else ENDPOINT_METAGRAPH
        data = await self._request("get", endpoint)
        return Metagraph(**data) if data else None

    async def get_block_hash(self, block_number: int) -> dict | None:
        return await self._request("get", ENDPOINT_BLOCK_HASH.format(block_number=block_number))

    async def get_epoch(self, block_number: int | None = None) -> Epoch | None:
        endpoint = f"{ENDPOINT_EPOCH}/{block_number}" if block_number else ENDPOINT_EPOCH
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

    async def get_raw_weights(self, epoch: int | None = None) -> dict | None:
        params = {"epoch": epoch} if epoch else {}
        return await self._request("get", ENDPOINT_RAW_WEIGHTS, params=params)

    async def force_commit_weights(self) -> dict | None:
        return await self._request("post", ENDPOINT_FORCE_COMMIT_WEIGHTS)

    async def get_commitment(self, hotkey: str, block: int | None = None) -> dict | None:
        params = {"block": block} if block else {}
        return await self._request("get", ENDPOINT_GET_COMMITMENT.format(hotkey=hotkey), params=params)

    async def get_commitments(self, block: int | None = None) -> dict | None:
        params = {"block": block} if block else {}
        return await self._request("get", ENDPOINT_GET_COMMITMENTS, params=params)

    async def set_commitment(self, data_hex: str) -> dict | None:
        return await self._request("post", ENDPOINT_SET_COMMITMENT, json={"data_hex": data_hex})
