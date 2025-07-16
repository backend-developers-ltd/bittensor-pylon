import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from litestar import Litestar, get, post, put
from litestar.connection import Request
from litestar.exceptions import NotFoundException
from litestar.response import Response
from litestar.status_codes import HTTP_404_NOT_FOUND

from .constants import (
    ENDPOINT_BLOCK_HASH,
    ENDPOINT_COMMITMENT,
    ENDPOINT_COMMITMENTS,
    ENDPOINT_EPOCH,
    ENDPOINT_FORCE_COMMIT_WEIGHTS,
    ENDPOINT_HYPERPARAMS,
    ENDPOINT_LATEST_BLOCK,
    ENDPOINT_LATEST_METAGRAPH,
    ENDPOINT_METAGRAPH,
    ENDPOINT_SET_COMMITMENT,
    ENDPOINT_SET_HYPERPARAM,
    ENDPOINT_SET_WEIGHT,
    ENDPOINT_UPDATE_WEIGHT,
    ENDPOINT_WEIGHTS,
)


class MockHooks(SimpleNamespace):
    get_latest_block: MagicMock
    get_metagraph: MagicMock
    get_block_hash: MagicMock
    get_epoch: MagicMock
    get_hyperparams: MagicMock
    set_hyperparam: MagicMock
    update_weight: MagicMock
    set_weight: MagicMock
    get_weights: MagicMock
    force_commit_weights: MagicMock
    get_commitment: MagicMock
    get_commitments: MagicMock
    set_commitment: MagicMock


class MockHandler:
    """A class to manage mocking the Pylon API by running a self-contained Litestar app."""

    def __init__(self, mock_data_path: str, base_url: str):
        with open(mock_data_path) as f:
            self.mock_data = json.load(f)
        self._overrides: dict[str, Any] = {}
        self.hooks = MockHooks(
            get_latest_block=MagicMock(),
            get_metagraph=MagicMock(),
            get_block_hash=MagicMock(),
            get_epoch=MagicMock(),
            get_hyperparams=MagicMock(),
            set_hyperparam=MagicMock(),
            update_weight=MagicMock(),
            set_weight=MagicMock(),
            get_weights=MagicMock(),
            force_commit_weights=MagicMock(),
            get_commitment=MagicMock(),
            get_commitments=MagicMock(),
            set_commitment=MagicMock(),
        )
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
        async def get_latest_block() -> Response:
            self.hooks.get_latest_block()
            if response := self._get_override_response("get_latest_block"):
                return response
            return Response({"block": self.mock_data["metagraph"]["block"]})

        @get([ENDPOINT_LATEST_METAGRAPH, ENDPOINT_METAGRAPH])
        async def get_metagraph(block_number: int | None = None) -> Response:
            self.hooks.get_metagraph(block_number=block_number)
            if response := self._get_override_response("get_metagraph"):
                return response
            return Response(self.mock_data["metagraph"])

        @get(ENDPOINT_BLOCK_HASH.format(block_number="{block_number:int}"))
        async def get_block_hash(block_number: int) -> Response:
            self.hooks.get_block_hash(block_number=block_number)
            if response := self._get_override_response("get_block_hash"):
                return response
            return Response({"block_hash": self.mock_data["metagraph"]["block_hash"]})

        @get([ENDPOINT_EPOCH, f"{ENDPOINT_EPOCH}/{{block_number:int}}"])
        async def get_epoch(block_number: int | None = None) -> Response:
            self.hooks.get_epoch(block_number=block_number)
            if response := self._get_override_response("get_epoch"):
                return response
            return Response(self.mock_data["epoch"])

        @get(ENDPOINT_HYPERPARAMS)
        async def get_hyperparams() -> Response:
            self.hooks.get_hyperparams()
            if response := self._get_override_response("get_hyperparams"):
                return response
            return Response(self.mock_data["hyperparams"])

        @put(ENDPOINT_SET_HYPERPARAM)
        async def set_hyperparam(data: dict[str, Any]) -> Response:
            self.hooks.set_hyperparam(**data)
            if response := self._get_override_response("set_hyperparam"):
                return response
            return Response({"detail": "Hyperparameter set successfully"})

        @put(ENDPOINT_UPDATE_WEIGHT)
        async def update_weight(data: dict[str, Any]) -> Response:
            self.hooks.update_weight(**data)
            if response := self._get_override_response("update_weight"):
                return response
            return Response({"detail": "Weight updated successfully"})

        @put(ENDPOINT_SET_WEIGHT)
        async def set_weight(data: dict[str, Any]) -> Response:
            self.hooks.set_weight(**data)
            if response := self._get_override_response("set_weight"):
                return response
            return Response({"detail": "Weight set successfully"})

        @get(ENDPOINT_WEIGHTS)
        async def get_weights(request: Request) -> Response:
            epoch_str = request.query_params.get("epoch")
            epoch = int(epoch_str) if epoch_str else None
            self.hooks.get_weights(epoch=epoch)
            if response := self._get_override_response("get_weights"):
                return response
            mock_weights = self.mock_data.get("weights", {})
            if epoch is not None and mock_weights.get("epoch") != epoch:
                raise NotFoundException(detail="Epoch weights not found")
            return Response(mock_weights)

        @post(ENDPOINT_FORCE_COMMIT_WEIGHTS)
        async def force_commit_weights() -> Response:
            self.hooks.force_commit_weights()
            if response := self._get_override_response("force_commit_weights"):
                return response
            return Response({"detail": "Weights committed successfully"})

        @get(ENDPOINT_COMMITMENT.format(hotkey="{hotkey:str}"))
        async def get_commitment(hotkey: str, request: Request) -> Response:
            block_str = request.query_params.get("block")
            block = int(block_str) if block_str else None
            self.hooks.get_commitment(hotkey=hotkey, block=block)
            if response := self._get_override_response("get_commitment"):
                return response
            commitment = self.mock_data["commitments"].get(hotkey)
            if commitment:
                return Response({"hotkey": hotkey, "commitment": commitment})
            raise NotFoundException(detail="Commitment not found")

        @get(ENDPOINT_COMMITMENTS)
        async def get_commitments(request: Request) -> Response:
            block_str = request.query_params.get("block")
            block = int(block_str) if block_str else None
            self.hooks.get_commitments(block=block)
            if response := self._get_override_response("get_commitments"):
                return response
            return Response(self.mock_data["commitments"])

        @post(ENDPOINT_SET_COMMITMENT)
        async def set_commitment(data: dict[str, str]) -> Response:
            self.hooks.set_commitment(**data)
            if response := self._get_override_response("set_commitment"):
                return response
            return Response({"detail": "Commitment set successfully"})

        def not_found_handler(request: Request, exc: NotFoundException) -> Response:
            return Response(content={"detail": "Not Found"}, status_code=HTTP_404_NOT_FOUND)

        return Litestar(
            route_handlers=[
                get_latest_block,
                get_metagraph,
                get_block_hash,
                get_epoch,
                get_hyperparams,
                set_hyperparam,
                update_weight,
                set_weight,
                get_weights,
                force_commit_weights,
                get_commitment,
                get_commitments,
                set_commitment,
            ],
            exception_handlers={HTTP_404_NOT_FOUND: not_found_handler},
        )
