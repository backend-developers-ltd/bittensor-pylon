"""Base classes and utilities shared between async and sync mock handlers."""

from types import SimpleNamespace
from unittest.mock import MagicMock


class MockHooks(SimpleNamespace):
    """Container for mock hooks that track API calls."""

    latest_block: MagicMock
    latest_metagraph: MagicMock
    metagraph: MagicMock
    block_hash: MagicMock
    epoch: MagicMock
    hyperparams: MagicMock
    set_hyperparam: MagicMock
    update_weight: MagicMock
    set_weight: MagicMock
    set_weights: MagicMock
    weights: MagicMock
    force_commit_weights: MagicMock
    commitment: MagicMock
    commitments: MagicMock
    set_commitment: MagicMock


def create_mock_hooks() -> MockHooks:
    """Create a new MockHooks instance with all hooks initialized."""
    return MockHooks(
        latest_block=MagicMock(),
        latest_metagraph=MagicMock(),
        metagraph=MagicMock(),
        block_hash=MagicMock(),
        epoch=MagicMock(),
        hyperparams=MagicMock(),
        set_hyperparam=MagicMock(),
        update_weight=MagicMock(),
        set_weight=MagicMock(),
        set_weights=MagicMock(),
        weights=MagicMock(),
        force_commit_weights=MagicMock(),
        commitment=MagicMock(),
        commitments=MagicMock(),
        set_commitment=MagicMock(),
    )
