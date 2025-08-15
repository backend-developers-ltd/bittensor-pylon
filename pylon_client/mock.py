"""Synchronous mock handler using WSGI for the sync PylonClient."""

import json
from typing import Any
from urllib.parse import parse_qs

from pylon_common.constants import (
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
)

from .mock_base import create_mock_hooks


class MockHandler:
    """A synchronous mock handler that creates a WSGI app for testing."""

    def __init__(self, mock_data_path: str, base_url: str):
        with open(mock_data_path) as f:
            self.mock_data = json.load(f)
        self._overrides: dict[str, Any] = {}
        self.hooks = create_mock_hooks()
        self.base_url = base_url

    def override(self, endpoint_name: str, json_response: dict[str, Any], status_code: int = 200):
        """Override a specific endpoint's response."""
        if not hasattr(self.hooks, endpoint_name):
            raise AttributeError(f"MockHandler has no endpoint named '{endpoint_name}'")
        self._overrides[endpoint_name] = (json_response, status_code)

    def wsgi_app(self, environ, start_response):
        """WSGI application that handles mock requests."""
        path = environ["PATH_INFO"]
        method = environ["REQUEST_METHOD"]
        query_string = environ.get("QUERY_STRING", "")

        # Parse query parameters
        query_params = parse_qs(query_string) if query_string else {}

        # Parse request body for POST/PUT
        body_data = None
        if method in ("POST", "PUT"):
            content_length = int(environ.get("CONTENT_LENGTH", 0))
            if content_length:
                body = environ["wsgi.input"].read(content_length)
                body_data = json.loads(body) if body else {}

        # Route to appropriate handler
        status, response_data = self._route_request(method, path, query_params, body_data)

        # Send response
        response_body = json.dumps(response_data).encode("utf-8")
        response_headers = [("Content-Type", "application/json"), ("Content-Length", str(len(response_body)))]

        status_text = f"{status} {'OK' if status == 200 else 'Error'}"
        start_response(status_text, response_headers)
        return [response_body]

    def _route_request(self, method: str, path: str, query_params: dict, body_data: dict | None):
        """Route the request to the appropriate handler."""

        # Latest block
        if method == "GET" and path == ENDPOINT_LATEST_BLOCK:
            self.hooks.latest_block()
            if override := self._overrides.get("latest_block"):
                return override[1], override[0]
            return 200, {"block": self.mock_data["metagraph"]["block"]}

        # Latest metagraph
        if method == "GET" and path == ENDPOINT_LATEST_METAGRAPH:
            self.hooks.latest_metagraph()
            if override := self._overrides.get("latest_metagraph"):
                return override[1], override[0]
            return 200, self.mock_data["metagraph"]

        # Metagraph by block
        if method == "GET" and path.startswith("/metagraph/"):
            block = int(path.split("/")[-1])
            self.hooks.metagraph(block=block)
            if override := self._overrides.get("metagraph"):
                return override[1], override[0]
            return 200, self.mock_data["metagraph"]

        # Block hash
        if method == "GET" and path.startswith("/block_hash/"):
            block = int(path.split("/")[-1])
            self.hooks.block_hash(block=block)
            if override := self._overrides.get("block_hash"):
                return override[1], override[0]
            return 200, {"block_hash": self.mock_data["metagraph"]["block_hash"]}

        # Epoch
        if method == "GET" and (path == ENDPOINT_EPOCH or path.startswith(f"{ENDPOINT_EPOCH}/")):
            block = None
            if "/" in path and len(path.split("/")) > 2:
                block = int(path.split("/")[-1])
            self.hooks.epoch(block=block)
            if override := self._overrides.get("epoch"):
                return override[1], override[0]
            return 200, self.mock_data["epoch"]

        # Hyperparams
        if method == "GET" and path == ENDPOINT_HYPERPARAMS:
            self.hooks.hyperparams()
            if override := self._overrides.get("hyperparams"):
                return override[1], override[0]
            return 200, self.mock_data["hyperparams"]

        # Set hyperparam
        if method == "PUT" and path == ENDPOINT_SET_HYPERPARAM:
            if body_data:
                self.hooks.set_hyperparam(**body_data)
            if override := self._overrides.get("set_hyperparam"):
                return override[1], override[0]
            return 200, {"detail": "Hyperparameter set successfully"}

        # Update weight
        if method == "PUT" and path == ENDPOINT_UPDATE_WEIGHT:
            if body_data:
                self.hooks.update_weight(**body_data)
            if override := self._overrides.get("update_weight"):
                return override[1], override[0]
            return 200, {"detail": "Weight updated successfully"}

        # Set weight
        if method == "PUT" and path == ENDPOINT_SET_WEIGHT:
            if body_data:
                self.hooks.set_weight(**body_data)
            if override := self._overrides.get("set_weight"):
                return override[1], override[0]
            return 200, {"detail": "Weight set successfully"}

        # Set weights (batch)
        if method == "PUT" and path == ENDPOINT_SET_WEIGHTS:
            if body_data:
                self.hooks.set_weights(**body_data)
            if override := self._overrides.get("set_weights"):
                return override[1], override[0]
            return 200, self.mock_data["set_weights"]

        # Latest weights
        if method == "GET" and path == ENDPOINT_LATEST_WEIGHTS:
            self.hooks.weights(block=None)
            if override := self._overrides.get("weights"):
                return override[1], override[0]
            weights_data = self.mock_data.get("weights", {})
            return 200, {"epoch": 1440, "weights": weights_data}

        # Weights by block
        if method == "GET" and path.startswith("/weights/"):
            block = int(path.split("/")[-1])
            self.hooks.weights(block=block)
            if override := self._overrides.get("weights"):
                return override[1], override[0]
            weights_data = self.mock_data.get("weights", {})
            return 200, {"epoch": 1440, "weights": weights_data}

        # Force commit weights
        if method == "POST" and path == ENDPOINT_FORCE_COMMIT_WEIGHTS:
            self.hooks.force_commit_weights()
            if override := self._overrides.get("force_commit_weights"):
                return override[1], override[0]
            return 201, {"detail": "Weights committed successfully"}

        # Get commitment
        if method == "GET" and path.startswith("/commitment/"):
            hotkey = path.split("/")[-1]
            block = None
            if "block" in query_params:
                block = int(query_params["block"][0])
            self.hooks.commitment(hotkey=hotkey, block=block)
            if override := self._overrides.get("commitment"):
                return override[1], override[0]
            commitment = self.mock_data["commitments"].get(hotkey)
            if commitment:
                return 200, {"hotkey": hotkey, "commitment": commitment}
            return 404, {"detail": "Commitment not found"}

        # Get all commitments
        if method == "GET" and path == ENDPOINT_COMMITMENTS:
            block = None
            if "block" in query_params:
                block = int(query_params["block"][0])
            self.hooks.commitments(block=block)
            if override := self._overrides.get("commitments"):
                return override[1], override[0]
            return 200, self.mock_data["commitments"]

        # Set commitment
        if method == "POST" and path == ENDPOINT_SET_COMMITMENT:
            if body_data:
                self.hooks.set_commitment(**body_data)
            if override := self._overrides.get("set_commitment"):
                return override[1], override[0]
            return 201, {"detail": "Commitment set successfully"}

        # Not found
        return 404, {"detail": "Not Found"}
