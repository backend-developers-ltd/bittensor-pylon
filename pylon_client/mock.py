import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import httpx

from .constants import (
    ENDPOINT_HYPERPARAMS,
    ENDPOINT_LATEST_BLOCK,
    ENDPOINT_METAGRAPH,
    ENDPOINT_SET_COMMITMENT,
    ENDPOINT_SET_WEIGHT,
    ENDPOINT_UPDATE_WEIGHT,
)


class MockHandler:
    """A class to manage mocking the Pylon API, asserting calls, and overriding default responses."""

    def __init__(self, mock_data_path: str, base_url: str):
        with open(mock_data_path) as f:
            self.mock_data = json.load(f)
        self.base_url = base_url
        self._overrides: dict[str, Any] = {}

        # MagicMocks for call assertions
        self.hooks = SimpleNamespace(
            get_latest_block=MagicMock(),
            get_metagraph=MagicMock(),
            get_hyperparams=MagicMock(),
            set_weight=MagicMock(),
            update_weight=MagicMock(),
            set_commitment=MagicMock(),
        )

    def override(self, endpoint_name: str, json_response: dict[str, Any], status_code: int = 200):
        """Overrides the default mock response for a specific endpoint."""
        if not hasattr(self.hooks, endpoint_name):
            raise AttributeError(f"MockHandler has no endpoint named '{endpoint_name}'")
        self._overrides[endpoint_name] = {"json": json_response, "status_code": status_code}

    def get_transport(self) -> httpx.MockTransport:
        """Creates and returns a mock transport configured with the dispatch logic."""
        callbacks = {
            f"GET:{self.base_url}{ENDPOINT_LATEST_BLOCK}": self._latest_block_callback,
            f"GET:{self.base_url}{ENDPOINT_METAGRAPH}": self._metagraph_callback,
            f"GET:{self.base_url}{ENDPOINT_HYPERPARAMS}": self._hyperparams_callback,
            f"PUT:{self.base_url}{ENDPOINT_SET_WEIGHT}": self._set_weight_callback,
            f"PUT:{self.base_url}{ENDPOINT_UPDATE_WEIGHT}": self._update_weight_callback,
            f"POST:{self.base_url}{ENDPOINT_SET_COMMITMENT}": self._set_commitment_callback,
        }

        def dispatch(request: httpx.Request) -> httpx.Response:
            key = f"{request.method}:{request.url}"
            if key in callbacks:
                return callbacks[key](request)
            return httpx.Response(404, json={"detail": "Not Found"})

        return httpx.MockTransport(dispatch)

    # --- Mock Callbacks ---
    def _latest_block_callback(self, request: httpx.Request) -> httpx.Response:
        self.hooks.get_latest_block()
        if "get_latest_block" in self._overrides:
            override = self._overrides["get_latest_block"]
            return httpx.Response(override["status_code"], json=override["json"])
        return httpx.Response(200, json={"block": self.mock_data["metagraph"]["block"]})

    def _metagraph_callback(self, request: httpx.Request) -> httpx.Response:
        self.hooks.get_metagraph()
        if "get_metagraph" in self._overrides:
            override = self._overrides["get_metagraph"]
            return httpx.Response(override["status_code"], json=override["json"])
        return httpx.Response(200, json=self.mock_data["metagraph"])

    def _hyperparams_callback(self, request: httpx.Request) -> httpx.Response:
        self.hooks.get_hyperparams()
        if "get_hyperparams" in self._overrides:
            override = self._overrides["get_hyperparams"]
            return httpx.Response(override["status_code"], json=override["json"])
        return httpx.Response(200, json=self.mock_data["hyperparams"])

    def _set_weight_callback(self, request: httpx.Request) -> httpx.Response:
        self.hooks.set_weight()
        return httpx.Response(200, json={"detail": "Weight set successfully"})

    def _update_weight_callback(self, request: httpx.Request) -> httpx.Response:
        self.hooks.update_weight()
        return httpx.Response(200, json={"detail": "Weight updated successfully"})

    def _set_commitment_callback(self, request: httpx.Request) -> httpx.Response:
        self.hooks.set_commitment()
        return httpx.Response(200, json={"detail": "Commitment set successfully"})
