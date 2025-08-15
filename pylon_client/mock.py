"""Synchronous mock handler using Flask for the sync PylonClient."""

import json
from typing import Any

from flask import Flask, jsonify, request

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
    endpoint_name,
)

from .mock_base import create_mock_hooks


class MockHandler:
    """A synchronous mock handler that creates a Flask app for testing."""

    def __init__(self, mock_data_path: str, base_url: str):
        with open(mock_data_path) as f:
            self.mock_data = json.load(f)
        self._overrides: dict[str, Any] = {}
        self.hooks = create_mock_hooks()
        # The base_url is not used by the mock app but is kept for client compatibility
        self.base_url = base_url
        self.mock_app = self._create_mock_app()

    def override(self, endpoint_name: str, json_response: dict[str, Any], status_code: int = 200):
        """Override a specific endpoint's response."""
        if not hasattr(self.hooks, endpoint_name):
            raise AttributeError(f"MockHandler has no endpoint named '{endpoint_name}'")
        self._overrides[endpoint_name] = (json_response, status_code)

    def _get_override_response(self, endpoint_name: str) -> tuple[dict[str, Any], int] | None:
        """Get override response if available."""
        if override := self._overrides.get(endpoint_name):
            return override[0], override[1]
        return None

    def _create_mock_app(self) -> Flask:
        """Creates a Flask app with all the mock endpoints."""
        app = Flask(__name__)

        @app.route(ENDPOINT_LATEST_BLOCK, methods=["GET"])
        def latest_block():
            self.hooks.latest_block()
            if override := self._get_override_response(endpoint_name(ENDPOINT_LATEST_BLOCK)):
                return jsonify(override[0]), override[1]
            return jsonify({"block": self.mock_data["metagraph"]["block"]})

        @app.route(ENDPOINT_LATEST_METAGRAPH, methods=["GET"])
        def latest_metagraph():
            self.hooks.latest_metagraph()
            if override := self._get_override_response(endpoint_name(ENDPOINT_LATEST_METAGRAPH)):
                return jsonify(override[0]), override[1]
            return jsonify(self.mock_data["metagraph"])

        @app.route("/metagraph/<int:block>", methods=["GET"])
        def metagraph(block: int):
            self.hooks.metagraph(block=block)
            if override := self._get_override_response(endpoint_name(ENDPOINT_METAGRAPH)):
                return jsonify(override[0]), override[1]
            return jsonify(self.mock_data["metagraph"])

        @app.route("/block_hash/<int:block>", methods=["GET"])
        def block_hash(block: int):
            self.hooks.block_hash(block=block)
            if override := self._get_override_response(endpoint_name(ENDPOINT_BLOCK_HASH)):
                return jsonify(override[0]), override[1]
            return jsonify({"block_hash": self.mock_data["metagraph"]["block_hash"]})

        @app.route(ENDPOINT_EPOCH, methods=["GET"])
        @app.route(f"{ENDPOINT_EPOCH}/<int:block>", methods=["GET"])
        def epoch(block: int | None = None):
            self.hooks.epoch(block=block)
            if override := self._get_override_response(endpoint_name(ENDPOINT_EPOCH)):
                return jsonify(override[0]), override[1]
            return jsonify(self.mock_data["epoch"])

        @app.route(ENDPOINT_HYPERPARAMS, methods=["GET"])
        def hyperparams():
            self.hooks.hyperparams()
            if override := self._get_override_response(endpoint_name(ENDPOINT_HYPERPARAMS)):
                return jsonify(override[0]), override[1]
            return jsonify(self.mock_data["hyperparams"])

        @app.route(ENDPOINT_SET_HYPERPARAM, methods=["PUT"])
        def set_hyperparam():
            data = request.get_json() or {}
            self.hooks.set_hyperparam(**data)
            if override := self._get_override_response(endpoint_name(ENDPOINT_SET_HYPERPARAM)):
                return jsonify(override[0]), override[1]
            return jsonify({"detail": "Hyperparameter set successfully"})

        @app.route(ENDPOINT_UPDATE_WEIGHT, methods=["PUT"])
        def update_weight():
            data = request.get_json() or {}
            self.hooks.update_weight(**data)
            if override := self._get_override_response(endpoint_name(ENDPOINT_UPDATE_WEIGHT)):
                return jsonify(override[0]), override[1]
            return jsonify({"detail": "Weight updated successfully"})

        @app.route(ENDPOINT_SET_WEIGHT, methods=["PUT"])
        def set_weight():
            data = request.get_json() or {}
            self.hooks.set_weight(**data)
            if override := self._get_override_response(endpoint_name(ENDPOINT_SET_WEIGHT)):
                return jsonify(override[0]), override[1]
            return jsonify({"detail": "Weight set successfully"})

        @app.route(ENDPOINT_SET_WEIGHTS, methods=["PUT"])
        def set_weights():
            data = request.get_json() or {}
            self.hooks.set_weights(**data)
            if override := self._get_override_response(endpoint_name(ENDPOINT_SET_WEIGHTS)):
                return jsonify(override[0]), override[1]
            return jsonify(self.mock_data["set_weights"])

        @app.route(ENDPOINT_LATEST_WEIGHTS, methods=["GET"])
        def latest_weights():
            self.hooks.weights(block=None)
            if override := self._get_override_response("weights"):
                return jsonify(override[0]), override[1]
            weights_data = self.mock_data.get("weights", {})
            return jsonify({"epoch": 1440, "weights": weights_data})

        @app.route("/weights/<int:block>", methods=["GET"])
        def weights(block: int):
            self.hooks.weights(block=block)
            if override := self._get_override_response("weights"):
                return jsonify(override[0]), override[1]
            weights_data = self.mock_data.get("weights", {})
            return jsonify({"epoch": 1440, "weights": weights_data})

        @app.route(ENDPOINT_FORCE_COMMIT_WEIGHTS, methods=["POST"])
        def force_commit_weights():
            self.hooks.force_commit_weights()
            if override := self._get_override_response(endpoint_name(ENDPOINT_FORCE_COMMIT_WEIGHTS)):
                return jsonify(override[0]), override[1]
            return jsonify({"detail": "Weights committed successfully"}), 201

        @app.route("/commitment/<string:hotkey>", methods=["GET"])
        def commitment(hotkey: str):
            block_str = request.args.get("block")
            block = int(block_str) if block_str else None
            self.hooks.commitment(hotkey=hotkey, block=block)
            if override := self._get_override_response(endpoint_name(ENDPOINT_COMMITMENT)):
                return jsonify(override[0]), override[1]
            commitment = self.mock_data["commitments"].get(hotkey)
            if commitment:
                return jsonify({"hotkey": hotkey, "commitment": commitment})
            return jsonify({"detail": "Commitment not found"}), 404

        @app.route(ENDPOINT_COMMITMENTS, methods=["GET"])
        def commitments():
            block_str = request.args.get("block")
            block = int(block_str) if block_str else None
            self.hooks.commitments(block=block)
            if override := self._get_override_response(endpoint_name(ENDPOINT_COMMITMENTS)):
                return jsonify(override[0]), override[1]
            return jsonify(self.mock_data["commitments"])

        @app.route(ENDPOINT_SET_COMMITMENT, methods=["POST"])
        def set_commitment():
            data = request.get_json() or {}
            self.hooks.set_commitment(**data)
            if override := self._get_override_response(endpoint_name(ENDPOINT_SET_COMMITMENT)):
                return jsonify(override[0]), override[1]
            return jsonify({"detail": "Commitment set successfully"}), 201

        @app.errorhandler(404)
        def not_found(error):
            return jsonify({"detail": "Not Found"}), 404

        return app
