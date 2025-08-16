import logging
from collections.abc import Callable
from typing import Any

import httpx
from httpx import Client, Limits, Timeout, TransportError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from pylon_common.constants import (
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
    ENDPOINT_SET_WEIGHTS,
    ENDPOINT_UPDATE_WEIGHT,
    ENDPOINT_WEIGHTS,
    format_endpoint,
)
from pylon_common.models import Epoch, Metagraph

logger = logging.getLogger(__name__)


class PylonClient:
    """A synchronous client for the bittensor-pylon service."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        client: Client | None = None,
        mock_data_path: str | None = None,
    ):
        """Initializes the PylonClient.

        Args:
            base_url: The base URL of the pylon service.
            timeout: The timeout for requests in seconds.
            max_retries: The maximum number of retries for failed requests.
            backoff_factor: The backoff factor for exponential backoff between retries.
            client: An optional pre-configured httpx.Client.
            mock_data_path: Path to a JSON file with mock data to run the client in mock mode.
        """
        self.base_url = base_url
        self._timeout = Timeout(timeout)
        self._limits = Limits(max_connections=100, max_keepalive_connections=20)
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client = client
        self._should_close_client = client is None
        self.mock: Any | None = None
        self.override: Callable[[str, Any], None] | None = None

        if mock_data_path:
            self._setup_mock_client(mock_data_path)

    def _setup_mock_client(self, mock_data_path: str):
        """Configures the client to use method-level mocking."""
        from .mock import MockHandler

        mock_handler = MockHandler(mock_data_path, self.base_url)
        self.mock = mock_handler.hooks
        self.override = mock_handler.override

        # Replace client methods with mock methods automatically
        for method_name in dir(mock_handler):
            if (
                not method_name.startswith("_")
                and hasattr(self, method_name)
                and callable(getattr(mock_handler, method_name))
            ):
                setattr(self, method_name, getattr(mock_handler, method_name))

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = Client(base_url=self.base_url, timeout=self._timeout, limits=self._limits)
        return self._client

    def close(self) -> None:
        """Close the HTTP client and clean up resources. Optional cleanup method."""
        if self._client and self._should_close_client:
            self._client.close()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(TransportError),
    )
    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Makes a synchronous HTTP request with error handling and retries."""
        try:
            response = self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.warning(f"An error occurred while requesting {e.request.url!r}: {e}")
            raise

    def get_latest_block(self) -> int | None:
        """Get the latest processed block number.

        Returns:
            int: The latest block number
        """
        data = self._request("get", ENDPOINT_LATEST_BLOCK)
        return data["block"] if data else None

    def get_metagraph(self, block: int | None = None) -> Metagraph | None:
        """Get the metagraph for the latest or specified block.

        Args:
            block: Optional block number. If None, returns latest metagraph.

        Returns:
            Metagraph: Object containing block, block_hash, and neurons dict
        """
        endpoint = f"/metagraph/{block}" if block else ENDPOINT_LATEST_METAGRAPH
        data = self._request("get", endpoint)
        return Metagraph(**data) if data else None

    def get_block_hash(self, block: int) -> str | None:
        """Get the block hash for a specific block number.

        Args:
            block: Block number to get hash for

        Returns:
            str: The block hash
        """
        data = self._request("get", format_endpoint(ENDPOINT_BLOCK_HASH, block=block))
        return data["block_hash"] if data else None

    def get_epoch(self, block: int | None = None) -> Epoch | None:
        """Get epoch information for the current or specified block.

        Args:
            block: Optional block number. If None, returns current epoch.

        Returns:
            Epoch: Object with epoch_start and epoch_end block numbers
        """
        endpoint = f"{ENDPOINT_EPOCH}/{block}" if block else ENDPOINT_EPOCH
        data = self._request("get", endpoint)
        return Epoch(**data) if data else None

    def get_hyperparams(self) -> dict | None:
        """Get cached subnet hyperparameters.

        Returns:
            dict: Subnet hyperparameters (structure varies by subnet)
        """
        return self._request("get", ENDPOINT_HYPERPARAMS)

    def set_hyperparam(self, name: str, value: Any) -> None:
        """Set a subnet hyperparameter (subnet owner only).

        Args:
            name: Hyperparameter name
            value: New value for the hyperparameter
        """
        self._request("put", ENDPOINT_SET_HYPERPARAM, json={"name": name, "value": value})

    def update_weight(self, hotkey: str, weight_delta: float) -> dict | None:
        """Update a hotkey's weight by a delta (validator only).

        Args:
            hotkey: Hotkey to update weight for
            weight_delta: Amount to change weight by (can be negative)

        Returns:
            dict: {'hotkey': str, 'weight': float, 'epoch': int}
        """
        return self._request("put", ENDPOINT_UPDATE_WEIGHT, json={"hotkey": hotkey, "weight_delta": weight_delta})

    def set_weight(self, hotkey: str, weight: float) -> dict | None:
        """Set a hotkey's weight (validator only).

        Args:
            hotkey: Hotkey to set weight for
            weight: New weight value

        Returns:
            dict: {'hotkey': str, 'weight': float, 'epoch': int}
        """
        return self._request("put", ENDPOINT_SET_WEIGHT, json={"hotkey": hotkey, "weight": weight})

    def set_weights(self, weights: dict[str, float]) -> dict | None:
        """Set multiple weights at once (validator only).

        Args:
            weights: Dict mapping hotkey to weight

        Returns:
            dict: {'weights': dict, 'epoch': int, 'count': int}
        """
        return self._request("put", ENDPOINT_SET_WEIGHTS, json={"weights": weights})

    def get_weights(self, block: int | None = None) -> dict | None:
        """Get weights for the current or specified epoch.

        Args:
            block: Optional block number. If None, returns latest weights.

        Returns:
            dict: {'epoch': int, 'weights': dict[str, float]}
        """
        if block is not None:
            endpoint = format_endpoint(ENDPOINT_WEIGHTS, block=block)
        else:
            endpoint = ENDPOINT_LATEST_WEIGHTS
        return self._request("get", endpoint)

    def force_commit_weights(self) -> dict | None:
        """Force commit current weights to the subnet (validator only).

        Returns:
            dict: Response from weight commit operation
        """
        return self._request("post", ENDPOINT_FORCE_COMMIT_WEIGHTS)

    def get_commitment(self, hotkey: str, block: int | None = None) -> str | None:
        """Get commitment for a specific hotkey.

        Args:
            hotkey: Hotkey to get commitment for
            block: Optional block number for historical commitment

        Returns:
            str: The commitment value
        """
        params = {"block": block} if block else {}
        data = self._request("get", format_endpoint(ENDPOINT_COMMITMENT, hotkey=hotkey), params=params)
        return data["commitment"] if data else None

    def get_commitments(self, block: int | None = None) -> dict | None:
        """Get all commitments for the subnet.

        Args:
            block: Optional block number for historical commitments

        Returns:
            dict: Dictionary of hotkey to commitment mappings
        """
        params = {"block": block} if block else {}
        return self._request("get", ENDPOINT_COMMITMENTS, params=params)

    def set_commitment(self, data_hex: str) -> None:
        """Set commitment for the app's wallet.

        Args:
            data_hex: Hex-encoded commitment data
        """
        self._request("post", ENDPOINT_SET_COMMITMENT, json={"data_hex": data_hex})
