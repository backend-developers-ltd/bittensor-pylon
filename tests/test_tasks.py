import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time
from litestar import Litestar

from pylon_common.settings import settings as app_settings
from pylon_service.tasks import fetch_latest_metagraph_task, set_weights_periodically_task
from pylon_service.utils import get_epoch_containing_block
from tests.conftest import MockBittensorClient, get_mock_metagraph

# Default settings for tests, can be overridden by monkeypatch
TEST_TEMPO = 100
TEST_COMMIT_CYCLE_LENGTH = 2
TEST_COMMIT_WINDOW_START_OFFSET = 50
TEST_COMMIT_WINDOW_END_BUFFER = 10
TEST_CHECK_INTERVAL = 0.3
TEST_LATEST_METAGRAPH_TASK_INTERVAL_SECONDS = 0.1


async def wait_for_mock_call(mock_obj, timeout=1.0, iterations=20):
    """Waits for an AsyncMock or MagicMock to be called."""
    for _ in range(iterations):
        if mock_obj.called:
            return True
        await asyncio.sleep(0)
    raise TimeoutError(f"Mock was not called within {timeout}s")


@pytest.fixture
def mock_app(monkeypatch):
    monkeypatch.setattr(app_settings, "tempo", TEST_TEMPO)
    monkeypatch.setattr(app_settings, "commit_cycle_length", TEST_COMMIT_CYCLE_LENGTH)
    monkeypatch.setattr(app_settings, "weight_commit_check_task_interval_seconds", TEST_CHECK_INTERVAL)
    monkeypatch.setattr(app_settings, "commit_window_start_offset", TEST_COMMIT_WINDOW_START_OFFSET)
    monkeypatch.setattr(app_settings, "commit_window_end_buffer", TEST_COMMIT_WINDOW_END_BUFFER)
    monkeypatch.setattr(app_settings, "fetch_latest_metagraph_task_interval_seconds", 0.1)

    app = Litestar(route_handlers=[])
    app.state.bittensor_client = MockBittensorClient()
    app.state.reveal_round = None
    app.state.last_commit_block = None
    return app


def update_app_state(app, block):
    app.state.latest_block = block
    app.state.current_epoch_start = get_epoch_containing_block(block).start
    app.state.metagraph_cache = {block: get_mock_metagraph(block)}


@pytest.mark.asyncio
@patch("pylon_service.tasks.commit_weights", new_callable=AsyncMock)
@patch("pylon_service.tasks.get_weights", new_callable=AsyncMock)
@patch("pylon_service.tasks.fetch_last_weight_commit_block", new_callable=AsyncMock)
async def test_set_weights_commit_flow(
    mock_fetch_last_commit,
    mock_get_weights,
    mock_commit_weights_call,
    mock_app,
):
    mock_fetch_last_commit.return_value = 0  # Start as if no prior commits
    mock_get_weights.return_value = {1: 0.5, 2: 0.5, 3: 0.5}

    with freeze_time("2023-01-01") as freezer:
        stop_event = asyncio.Event()
        task_handle = asyncio.create_task(set_weights_periodically_task(mock_app, stop_event))

        # Allow task to initialize and run the first check
        freezer.tick(TEST_CHECK_INTERVAL)  # Ensure task wakes and processes
        await asyncio.sleep(0)  # Allow the task to run its checks
        # The task should have fetched the last commit block on startup
        mock_fetch_last_commit.assert_called_once()

        # 1: FAIL: Initial state, not enough tempos, not in window
        mock_app.state.latest_block = TEST_TEMPO // 2  # Half a tempo, not enough
        freezer.tick(TEST_CHECK_INTERVAL)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()
        assert mock_app.state.last_commit_block is None

        # 2: FAIL: Enough tempos, but NOT in commit window
        mock_app.state.latest_block = TEST_TEMPO * TEST_COMMIT_CYCLE_LENGTH  # Enough tempos
        freezer.tick(TEST_CHECK_INTERVAL)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()
        assert mock_app.state.last_commit_block is None

        # 3: SUCCESS: Enough tempos AND in commit window
        current_block_for_commit = (
            TEST_TEMPO * TEST_COMMIT_CYCLE_LENGTH + TEST_COMMIT_WINDOW_START_OFFSET + 3
        )  # third block in the window
        update_app_state(mock_app, current_block_for_commit)  # metagraph cache should have latest block data
        mock_commit_weights_call.return_value = current_block_for_commit + 1  # reveal round one block later

        freezer.tick(TEST_CHECK_INTERVAL)
        assert await wait_for_mock_call(mock_get_weights)
        assert await wait_for_mock_call(mock_commit_weights_call)

        mock_get_weights.assert_called_once()
        mock_get_weights.reset_mock()
        mock_commit_weights_call.assert_called_once()

        # check last succesfull commit block or reveal round were updated
        assert mock_app.state.last_commit_block == current_block_for_commit
        assert mock_app.state.reveal_round == current_block_for_commit + 1
        previously_set_commit_block = mock_app.state.last_commit_block

        mock_commit_weights_call.reset_mock()

        # 4: FAIL: Just committed, not enough tempos since last commit but in window
        current_block_for_commit = current_block_for_commit + 2  # move another two blocks, still in window
        update_app_state(mock_app, current_block_for_commit)
        freezer.tick(TEST_CHECK_INTERVAL)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()

        # check last succesfull commit block or reveal round were not changed
        assert mock_app.state.last_commit_block == previously_set_commit_block
        assert mock_app.state.reveal_round == previously_set_commit_block + 1

        # 5: SUCCESS: Enough tempos passed again, and in a new commit window
        current_block_for_second_commit = current_block_for_commit + (TEST_TEMPO * TEST_COMMIT_CYCLE_LENGTH)
        mock_commit_weights_call.return_value = current_block_for_second_commit + 1  # reveal round one block later

        update_app_state(mock_app, current_block_for_second_commit)

        freezer.tick(TEST_CHECK_INTERVAL)
        await wait_for_mock_call(mock_get_weights)
        await wait_for_mock_call(mock_commit_weights_call)

        mock_get_weights.assert_called_once()
        mock_commit_weights_call.assert_called_once()

        # check last succesfull commit block or reveal round were updated
        assert mock_app.state.last_commit_block == current_block_for_second_commit
        assert mock_app.state.reveal_round == current_block_for_second_commit + 1

        stop_event.set()
        await task_handle


@pytest.mark.asyncio
@patch("pylon_service.tasks.cache_metagraph", new_callable=AsyncMock)
async def test_fetch_latest_metagraph_task_error_recovery(
    mock_cache_metagraph,
    mock_app,
):
    """Test that fetch_latest_metagraph_task continues to work after errors in different parts of the process"""
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
    await asyncio.sleep(0.4)
    assert mock_cache_metagraph.call_count == 2
    assert mock_app.state.latest_block == 100

    stop_event.set()
    await task_handle
