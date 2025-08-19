import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from pylon_common.models import Epoch, Metagraph


class MethodHooks(SimpleNamespace):
    def __init__(self):
        """Create a new MockHooks instance with all hooks initialized."""
        self.get_latest_block = MagicMock()
        self.get_metagraph = MagicMock()
        self.get_block_hash = MagicMock()
        self.get_epoch = MagicMock()
        self.get_hyperparams = MagicMock()
        self.set_hyperparam = MagicMock()
        self.update_weight = MagicMock()
        self.set_weight = MagicMock()
        self.set_weights = MagicMock()
        self.get_weights = MagicMock()
        self.force_commit_weights = MagicMock()
        self.get_commitment = MagicMock()
        self.get_commitments = MagicMock()
        self.set_commitment = MagicMock()


class MockHandler:
    def __init__(self, mock_data_path: str, base_url: str):
        with open(mock_data_path) as f:
            self.mock_data = json.load(f)
        self._overrides: dict[str, Any] = {}
        self.hooks = MethodHooks()

    def override(self, method_name: str, response: Any):
        if not hasattr(self.hooks, method_name):
            raise AttributeError(f"MockHandler has no method named '{method_name}'")
        self._overrides[method_name] = response

    def get_latest_block(self) -> int:
        self.hooks.get_latest_block()
        if "get_latest_block" in self._overrides:
            return self._overrides["get_latest_block"]
        return self.mock_data["metagraph"]["block"]

    def get_metagraph(self, block: int | None = None) -> Metagraph:
        self.hooks.get_metagraph(block=block)
        if "get_metagraph" in self._overrides:
            data = self._overrides["get_metagraph"]
            return Metagraph(**data) if isinstance(data, dict) else data
        return Metagraph(**self.mock_data["metagraph"])

    def get_block_hash(self, block: int) -> str:
        self.hooks.get_block_hash(block=block)
        if "get_block_hash" in self._overrides:
            return self._overrides["get_block_hash"]
        return self.mock_data["metagraph"]["block_hash"]

    def get_epoch(self, block: int | None = None) -> Epoch:
        self.hooks.get_epoch(block=block)
        if "get_epoch" in self._overrides:
            data = self._overrides["get_epoch"]
            return Epoch(**data) if isinstance(data, dict) else data
        return Epoch(**self.mock_data["epoch"])

    def get_hyperparams(self) -> dict:
        self.hooks.get_hyperparams()
        if "get_hyperparams" in self._overrides:
            return self._overrides["get_hyperparams"]
        return self.mock_data["hyperparams"]

    def set_hyperparam(self, name: str, value: Any) -> None:
        self.hooks.set_hyperparam(name=name, value=value)

    def update_weight(self, hotkey: str, weight_delta: float) -> dict:
        self.hooks.update_weight(hotkey=hotkey, weight_delta=weight_delta)
        if "update_weight" in self._overrides:
            return self._overrides["update_weight"]
        return {"detail": "Weight updated successfully"}

    def set_weight(self, hotkey: str, weight: float) -> dict:
        self.hooks.set_weight(hotkey=hotkey, weight=weight)
        if "set_weight" in self._overrides:
            return self._overrides["set_weight"]
        return {"detail": "Weight set successfully"}

    def set_weights(self, weights: dict[str, float]) -> dict:
        self.hooks.set_weights(weights=weights)
        if "set_weights" in self._overrides:
            return self._overrides["set_weights"]
        epoch_data = self.mock_data["epoch"]
        return self.mock_data.get(
            "set_weights", {"weights": weights, "epoch": epoch_data["start"], "count": len(weights)}
        )

    def get_weights(self, block: int | None = None) -> dict:
        self.hooks.get_weights(block=block)
        if "get_weights" in self._overrides:
            return self._overrides["get_weights"]
        weights_data = self.mock_data.get("weights", {})
        epoch_data = self.mock_data["epoch"]
        return {"epoch": epoch_data["start"], "weights": weights_data}

    def force_commit_weights(self) -> dict:
        self.hooks.force_commit_weights()
        if "force_commit_weights" in self._overrides:
            return self._overrides["force_commit_weights"]
        return {"detail": "Weights committed successfully"}

    def get_commitment(self, hotkey: str, block: int | None = None) -> str:
        self.hooks.get_commitment(hotkey=hotkey, block=block)
        if "get_commitment" in self._overrides:
            return self._overrides["get_commitment"]
        return self.mock_data["commitments"].get(hotkey, "0x0000")

    def get_commitments(self, block: int | None = None) -> dict:
        self.hooks.get_commitments(block=block)
        if "get_commitments" in self._overrides:
            return self._overrides["get_commitments"]
        return self.mock_data["commitments"]

    def set_commitment(self, data_hex: str) -> None:
        self.hooks.set_commitment(data_hex=data_hex)
