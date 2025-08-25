import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time

from pylon_common.settings import settings
from pylon_service.tasks import commit_weights_task, fetch_latest_metagraph_task
from pylon_service.utils import get_epoch_containing_block
from tests.conftest import get_mock_metagraph


async def wait_for_mock_call(mock_obj, timeout=1.0, iterations=20):
    """Waits for an AsyncMock or MagicMock to be called."""
    for _ in range(iterations):
        if mock_obj.called:
            return True
        await asyncio.sleep(0)
    raise TimeoutError(f"Mock was not called within {timeout}s")


@pytest.fixture(autouse=True)
def patch_envs(monkeypatch):
    monkeypatch.setenv("TEMPO", "100")
    monkeypatch.setenv("COMMIT_CYCLE_LENGTH", "2")
    monkeypatch.setenv("COMMIT_WINDOW_START_OFFSET", "50")
    monkeypatch.setenv("COMMIT_WINDOW_END_BUFFER", "10")
    monkeypatch.setenv("COMMIT_WEIGHTS_TASK_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("FETCH_LATEST_METAGRAPH_TASK_INTERVAL_SECONDS", "1")


def update_app_state(app, block):
    app.state.latest_block = block
    app.state.current_epoch_start = get_epoch_containing_block(block).start
    app.state.metagraph_cache = {block: get_mock_metagraph(block)}


@pytest.mark.asyncio
@patch("pylon_service.tasks.commit_weights", new_callable=AsyncMock)
@patch("pylon_service.tasks.get_weights", new_callable=AsyncMock)
@patch("pylon_service.tasks.fetch_block_last_weight_commit", new_callable=AsyncMock)
async def test_set_weights_commit_flow(test_client, mock_get_weights, mock_commit_weights_call, mock_fetch_last_commit):
    mock_app = test_client.app
    mock_fetch_last_commit.return_value = 0  # Start as if no prior commits
    mock_get_weights.return_value = {1: 0.5, 2: 0.5, 3: 0.5}

    # Track the last successful commit block
    last_commit = 0

    def mock_commit_side_effect(app, weights):
        nonlocal last_commit
        last_commit = app.state.latest_block
        app.state.last_commit_block = last_commit
        return last_commit + 1  # Return reveal round

    mock_commit_weights_call.side_effect = mock_commit_side_effect

    # Initialize app state for the new architecture
    mock_app.state.last_commit_block = 0  # Start with no prior commits

    check_interval = settings.commit_weights_task_interval_seconds
    with freeze_time("2023-01-01") as freezer:
        stop_event = asyncio.Event()
        task_handle = asyncio.create_task(commit_weights_task(mock_app, stop_event))

        freezer.tick(check_interval)  # Ensure task wakes and processes
        await asyncio.sleep(0.0)  # Allow the task to run its checks

        # 1: FAIL: Initial state, not enough tempos, not in window
        mock_app.state.latest_block = settings.tempo // 2  # Half a tempo, not enough
        freezer.tick(check_interval)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()
        assert mock_app.state.last_commit_block == 0

        # 2: FAIL: Enough tempos, but NOT in commit window
        mock_app.state.latest_block = settings.tempo * settings.commit_cycle_length  # Enough tempos
        freezer.tick(check_interval)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()
        assert mock_app.state.last_commit_block == 0

        # 3: SUCCESS: Enough tempos AND in commit window
        current_block_for_commit = (
            settings.tempo * settings.commit_cycle_length + settings.commit_window_start_offset + 3
        )  # third block in the window
        update_app_state(mock_app, current_block_for_commit)  # metagraph cache should have latest block data

        freezer.tick(check_interval)
        assert await wait_for_mock_call(mock_get_weights)
        assert await wait_for_mock_call(mock_commit_weights_call)

        mock_get_weights.assert_called_once()
        mock_get_weights.reset_mock()
        mock_commit_weights_call.assert_called_once()

        # check last succesfull commit block or reveal round were updated
        # Verify that our side effect was called with the correct block
        assert last_commit == current_block_for_commit
        assert mock_app.state.reveal_round == current_block_for_commit + 1
        previously_set_commit_block = current_block_for_commit

        mock_commit_weights_call.reset_mock()

        # 4: FAIL: Just committed, not enough tempos since last commit but in window
        current_block_for_commit = current_block_for_commit + 2  # move another two blocks, still in window
        update_app_state(mock_app, current_block_for_commit)
        freezer.tick(check_interval)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()

        # check last succesfull commit block or reveal round were not changed
        # The tracking variable should still have the previous commit block
        assert last_commit == previously_set_commit_block
        assert mock_app.state.reveal_round == previously_set_commit_block + 1

        # 5: SUCCESS: Enough tempos passed again, and in a new commit window
        current_block_for_second_commit = current_block_for_commit + (settings.tempo * settings.commit_cycle_length)

        update_app_state(mock_app, current_block_for_second_commit)

        freezer.tick(check_interval)
        await wait_for_mock_call(mock_get_weights)
        await wait_for_mock_call(mock_commit_weights_call)

        mock_get_weights.assert_called_once()
        mock_commit_weights_call.assert_called_once()

        # check last succesfull commit block or reveal round were updated
        # Verify that our side effect was called with the second commit block
        assert last_commit == current_block_for_second_commit
        assert mock_app.state.reveal_round == current_block_for_second_commit + 1

    stop_event.set()
    await task_handle


@pytest.mark.asyncio
@patch("pylon_service.tasks.cache_metagraph", new_callable=AsyncMock)
async def test_fetch_latest_metagraph_task_error_recovery(
    mock_cache_metagraph,
    test_client,
):
    """Test that fetch_latest_metagraph_task continues to work after errors in different parts of the process"""
    mock_app = test_client.app
    mock_app.state.latest_block = None
    mock_app.state.current_epoch_start = None

    # Mock successful block fetching
    mock_app.state.bittensor_client.head.get.return_value = MagicMock(number=100, hash="0xabc")

    # fails on first call, succeeds on second
    mock_cache_metagraph.side_effect = [Exception("Cache failed"), None]

    stop_event = asyncio.Event()
    task_handle = asyncio.create_task(fetch_latest_metagraph_task(mock_app, stop_event))

    # Allow task to run first iteration (should fail)
    await wait_for_mock_call(mock_cache_metagraph, timeout=1.0)

    assert mock_cache_metagraph.call_count == 1
    assert mock_app.state.latest_block is None

    # Allow task to run second iteration (should succeed)
    await asyncio.sleep(settings.fetch_latest_metagraph_task_interval_seconds + 0.1)
    assert mock_cache_metagraph.call_count == 2
    assert mock_app.state.latest_block == 100

    stop_event.set()
    await task_handle
