import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time
from litestar import Litestar

from app.settings import settings as app_settings
from app.tasks import set_weights_periodically_task
from app.utils import get_epoch_containing_block
from tests.conftest import get_mock_metagraph

# Default settings for tests, can be overridden by monkeypatch
TEST_TEMPO = 100
TEST_COMMIT_CYCLE_LENGTH = 2  # Every 2 tempos
TEST_COMMIT_WINDOW_START_OFFSET = 50  # from start of tempo
TEST_COMMIT_WINDOW_END_BUFFER = 10  # from end of tempo
TEST_CHECK_INTERVAL = 0.01  # seconds, for fast checking


@pytest.fixture
def mock_app(monkeypatch):
    monkeypatch.setattr(app_settings, "tempo", TEST_TEMPO)
    monkeypatch.setattr(app_settings, "commit_reveal_cycle_length", TEST_COMMIT_CYCLE_LENGTH)
    monkeypatch.setattr(app_settings, "weight_commit_check_task_interval_seconds", TEST_CHECK_INTERVAL)
    monkeypatch.setattr(app_settings, "commit_window_start_offset", TEST_COMMIT_WINDOW_START_OFFSET)
    monkeypatch.setattr(app_settings, "commit_window_end_buffer", TEST_COMMIT_WINDOW_END_BUFFER)

    app = Litestar(route_handlers=[])
    app.state.bittensor_client = MagicMock()
    return app


def update_app_state(app, block):
    app.state.latest_block = block
    app.state.current_epoch_start = get_epoch_containing_block(block).epoch_start
    app.state.metagraph_cache = {block: get_mock_metagraph(block)}


@pytest.mark.asyncio
@patch("app.tasks.commit_weights", new_callable=AsyncMock)
@patch("app.tasks.get_latest_weights", new_callable=AsyncMock)
@patch("app.tasks.fetch_last_weight_commit_block", new_callable=AsyncMock)
async def test_set_weights_commit_flow(
    mock_fetch_last_commit,
    mock_get_latest_weights,
    mock_commit_weights_call,
    mock_app,
):
    mock_fetch_last_commit.return_value = 0  # Start as if no prior commits
    mock_get_latest_weights.return_value = {1: 0.5, 2: 0.5, 3: 0.5}

    with freeze_time("2023-01-01") as freezer:
        stop_event = asyncio.Event()
        task_handle = asyncio.create_task(set_weights_periodically_task(mock_app, stop_event))

        # Allow task to initialize and run the first check
        freezer.tick(TEST_CHECK_INTERVAL * 1.5)
        await asyncio.sleep(0)
        # The task should have fetched the last commit block on startup
        mock_fetch_last_commit.assert_called_once()

        # 1: FAIL: Initial state, not enough tempos, not in window
        mock_app.state.latest_block = TEST_TEMPO // 2  # Half a tempo, not enough
        freezer.tick(TEST_CHECK_INTERVAL)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()

        # 2: FAIL: Enough tempos, but NOT in commit window
        mock_app.state.latest_block = TEST_TEMPO * TEST_COMMIT_CYCLE_LENGTH  # Enough tempos
        freezer.tick(TEST_CHECK_INTERVAL)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()

        # 3: SUCCESS: Enough tempos AND in commit window
        current_block_for_commit = (
            TEST_TEMPO * TEST_COMMIT_CYCLE_LENGTH + TEST_COMMIT_WINDOW_START_OFFSET + 3
        )  # third block in the window
        update_app_state(mock_app, current_block_for_commit)  # metagraph cache should have latest block data
        freezer.tick(TEST_CHECK_INTERVAL)
        await asyncio.sleep(0)
        await asyncio.sleep(0)  # make sure it gets to the await
        mock_get_latest_weights.assert_called_once()
        mock_get_latest_weights.reset_mock()
        mock_commit_weights_call.assert_called_once()
        mock_commit_weights_call.reset_mock()

        # 4: FAIL: Just committed, not enough tempos since last commit but in window
        current_block_for_commit = current_block_for_commit + 2  # move another two blocks, still in window
        update_app_state(mock_app, current_block_for_commit)
        freezer.tick(TEST_CHECK_INTERVAL)
        await asyncio.sleep(0)
        mock_commit_weights_call.assert_not_called()

        # 5: SUCCESS: Enough tempos passed again, and in a new commit window
        current_block_for_second_commit = current_block_for_commit + (TEST_TEMPO * TEST_COMMIT_CYCLE_LENGTH)
        update_app_state(mock_app, current_block_for_second_commit)

        freezer.tick(TEST_CHECK_INTERVAL)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)  # make sure it gets to the await
        mock_get_latest_weights.assert_called_once()
        mock_commit_weights_call.assert_called_once()

        # --- Cleanup ---
        stop_event.set()
        await task_handle
