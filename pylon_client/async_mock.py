import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from litestar import Litestar, get, post, put
from litestar.connection import Request
from litestar.exceptions import NotFoundException
from litestar.response import Response
from litestar.status_codes import HTTP_404_NOT_FOUND

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
    ENDPOINT_METAGRAPH,
    ENDPOINT_SET_COMMITMENT,
    ENDPOINT_SET_HYPERPARAM,
    ENDPOINT_SET_WEIGHT,
    ENDPOINT_SET_WEIGHTS,
    ENDPOINT_UPDATE_WEIGHT,
    ENDPOINT_WEIGHTS,
    endpoint_name,
)


class TransportHooks(SimpleNamespace):
    def __init__(self):
        """Create a new MockHooks instance with all hooks initialized."""
        self.latest_block = MagicMock()
        self.latest_metagraph = MagicMock()
        self.metagraph = MagicMock()
        self.block_hash = MagicMock()
        self.epoch = MagicMock()
        self.hyperparams = MagicMock()
        self.set_hyperparam = MagicMock()
        self.update_weight = MagicMock()
        self.set_weight = MagicMock()
        self.set_weights = MagicMock()
        self.weights = MagicMock()
        self.force_commit_weights = MagicMock()
        self.commitment = MagicMock()
        self.commitments = MagicMock()
        self.set_commitment = MagicMock()


class AsyncMockHandler:
    """A class to manage mocking the Pylon API by running a self-contained Litestar app."""

    def __init__(self, mock_data_path: str, base_url: str):
        with open(mock_data_path) as f:
            self.mock_data = json.load(f)
        self._overrides: dict[str, Any] = {}
        self.hooks = TransportHooks()
        # The base_url is not used by the mock app but is kept for client compatibility
        self.base_url = base_url
        self.mock_app = self._create_mock_app()

    def override(self, endpoint_name: str, json_response: dict[str, Any], status_code: int = 200):
        if not hasattr(self.hooks, endpoint_name):
            raise AttributeError(f"MockHandler has no endpoint named '{endpoint_name}'")
        self._overrides[endpoint_name] = Response(content=json_response, status_code=status_code)

    def get_app(self) -> Litestar:
        """Creates a mock transport that routes requests to the internal Litestar app."""
        return self.mock_app

    def _get_override_response(self, endpoint_name: str) -> Response | None:
        return self._overrides.get(endpoint_name)

    def _create_mock_app(self) -> Litestar:
        """Creates a Litestar app with all the mock endpoints."""

        @get(ENDPOINT_LATEST_BLOCK)
        async def latest_block() -> Response:
            self.hooks.latest_block()
            if response := self._get_override_response(endpoint_name(ENDPOINT_LATEST_BLOCK)):
                return response
            return Response({"block": self.mock_data["metagraph"]["block"]})

        @get(ENDPOINT_LATEST_METAGRAPH)
        async def latest_metagraph() -> Response:
            self.hooks.latest_metagraph()
            if response := self._get_override_response(endpoint_name(ENDPOINT_LATEST_METAGRAPH)):
                return response
            return Response(self.mock_data["metagraph"])

        @get(ENDPOINT_METAGRAPH)
        async def metagraph(block: int) -> Response:
            self.hooks.metagraph(block=block)
            if response := self._get_override_response(endpoint_name(ENDPOINT_METAGRAPH)):
                return response
            return Response(self.mock_data["metagraph"])

        @get(ENDPOINT_BLOCK_HASH)
        async def block_hash(block: int) -> Response:
            self.hooks.block_hash(block=block)
            if response := self._get_override_response(endpoint_name(ENDPOINT_BLOCK_HASH)):
                return response
            return Response({"block_hash": self.mock_data["metagraph"]["block_hash"]})

        @get([ENDPOINT_EPOCH, f"{ENDPOINT_EPOCH}/{{block:int}}"])
        async def epoch(block: int | None = None) -> Response:
            self.hooks.epoch(block=block)
            if response := self._get_override_response(endpoint_name(ENDPOINT_EPOCH)):
                return response
            return Response(self.mock_data["epoch"])

        @get(ENDPOINT_HYPERPARAMS)
        async def hyperparams() -> Response:
            self.hooks.hyperparams()
            if response := self._get_override_response(endpoint_name(ENDPOINT_HYPERPARAMS)):
                return response
            return Response(self.mock_data["hyperparams"])

        @put(ENDPOINT_SET_HYPERPARAM)
        async def set_hyperparam(data: dict[str, Any]) -> Response:
            self.hooks.set_hyperparam(**data)
            if response := self._get_override_response(endpoint_name(ENDPOINT_SET_HYPERPARAM)):
                return response
            return Response({"detail": "Hyperparameter set successfully"})

        @put(ENDPOINT_UPDATE_WEIGHT)
        async def update_weight(data: dict[str, Any]) -> Response:
            self.hooks.update_weight(**data)
            if response := self._get_override_response(endpoint_name(ENDPOINT_UPDATE_WEIGHT)):
                return response
            return Response({"detail": "Weight updated successfully"})

        @put(ENDPOINT_SET_WEIGHT)
        async def set_weight(data: dict[str, Any]) -> Response:
            self.hooks.set_weight(**data)
            if response := self._get_override_response(endpoint_name(ENDPOINT_SET_WEIGHT)):
                return response
            return Response({"detail": "Weight set successfully"})

        @put(ENDPOINT_SET_WEIGHTS)
        async def set_weights(data: dict[str, Any]) -> Response:
            self.hooks.set_weights(**data)
            if response := self._get_override_response(endpoint_name(ENDPOINT_SET_WEIGHTS)):
                return response
            return Response(self.mock_data["set_weights"])

        @get(ENDPOINT_LATEST_WEIGHTS)
        async def latest_weights() -> Response:
            self.hooks.weights(block=None)
            if response := self._get_override_response("weights"):
                return response
            weights_data = self.mock_data.get("weights", {})
            return Response({"epoch": 1440, "weights": weights_data})

        @get(ENDPOINT_WEIGHTS)
        async def weights(block: int) -> Response:
            self.hooks.weights(block=block)
            if response := self._get_override_response("weights"):
                return response
            weights_data = self.mock_data.get("weights", {})
            return Response({"epoch": 1440, "weights": weights_data})

        @post(ENDPOINT_FORCE_COMMIT_WEIGHTS)
        async def force_commit_weights() -> Response:
            self.hooks.force_commit_weights()
            if response := self._get_override_response(endpoint_name(ENDPOINT_FORCE_COMMIT_WEIGHTS)):
                return response
            return Response({"detail": "Weights committed successfully"})

        @get(ENDPOINT_COMMITMENT)
        async def commitment(hotkey: str, request: Request) -> Response:
            block_str = request.query_params.get("block")
            block = int(block_str) if block_str else None
            self.hooks.commitment(hotkey=hotkey, block=block)
            if response := self._get_override_response(endpoint_name(ENDPOINT_COMMITMENT)):
                return response
            commitment = self.mock_data["commitments"].get(hotkey)
            if commitment:
                return Response({"hotkey": hotkey, "commitment": commitment})
            raise NotFoundException(detail="Commitment not found")

        @get(ENDPOINT_COMMITMENTS)
        async def commitments(request: Request) -> Response:
            block_str = request.query_params.get("block")
            block = int(block_str) if block_str else None
            self.hooks.commitments(block=block)
            if response := self._get_override_response(endpoint_name(ENDPOINT_COMMITMENTS)):
                return response
            return Response(self.mock_data["commitments"])

        @post(ENDPOINT_SET_COMMITMENT)
        async def set_commitment(data: dict[str, str]) -> Response:
            self.hooks.set_commitment(**data)
            if response := self._get_override_response(endpoint_name(ENDPOINT_SET_COMMITMENT)):
                return response
            return Response({"detail": "Commitment set successfully"})

        def not_found_handler(request: Request, exc: NotFoundException) -> Response:
            return Response(content={"detail": "Not Found"}, status_code=HTTP_404_NOT_FOUND)

        return Litestar(
            route_handlers=[
                latest_block,
                latest_metagraph,
                metagraph,
                block_hash,
                epoch,
                hyperparams,
                set_hyperparam,
                update_weight,
                set_weight,
                set_weights,
                latest_weights,
                weights,
                force_commit_weights,
                commitment,
                commitments,
                set_commitment,
            ],
            exception_handlers={HTTP_404_NOT_FOUND: not_found_handler},
        )
