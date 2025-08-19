import asyncio
import logging

from pylon_common.settings import settings
from pylon_service.bittensor_client import (
    cache_metagraph,
    commit_weights,
    fetch_last_weight_commit_block,
    get_weights,
)
from pylon_service.utils import CommitWindow, get_epoch_containing_block

logger = logging.getLogger(__name__)


async def fetch_latest_hyperparams_task(app, stop_event: asyncio.Event):
    """
    Periodically fetch and cache subnet hyperparameters in app.state.hyperparams as a dict.
    """
    stop_task = asyncio.create_task(stop_event.wait())
    while not stop_event.is_set():
        try:
            await fetch_hyperparams(app)
        except Exception as e:
            logger.error(f"Failed to fetch subnet hyperparameters: {e}")
        await asyncio.wait([stop_task], timeout=settings.fetch_hyperparams_task_interval_seconds)


async def fetch_hyperparams(app):
    subnet = app.state.bittensor_client.subnet(settings.bittensor_netuid)
    new_hyperparams = await subnet.get_hyperparameters()
    current_hyperparams = app.state.hyperparams
    for k, v in new_hyperparams.items():
        old_v = current_hyperparams.get(k, None)
        if old_v != v:
            logger.debug(f"Subnet hyperparame update: {k}: {old_v} -> {v}")
            app.state.hyperparams[k] = v


async def set_weights_periodically_task(app, stop_event: asyncio.Event):
    """
    Periodically checks conditions and commits weights to the Bittensor network.
    Commits weights every N tempos, only if within the specified commit window.
    """

    stop_task = asyncio.create_task(stop_event.wait())
    last_successful_commit_block = await fetch_last_weight_commit_block(app) or 0
    logger.info(f"Initial last successful commit block: {last_successful_commit_block}")

    while not stop_event.is_set():
        await asyncio.wait([stop_task], timeout=settings.weight_commit_check_task_interval_seconds)

        try:
            current_block = app.state.latest_block
            if current_block is None:
                logger.error("Could not retrieve current block. Retrying later.")
                continue

            # Check if we need to commit weights
            window = CommitWindow(current_block)
            tempos_since_last_commit = (current_block - last_successful_commit_block) // settings.tempo

            logger.debug(
                f"Checking weight commit conditions: current_block={current_block}, "
                f"last_commit_block={last_successful_commit_block}, tempos_passed={tempos_since_last_commit}, "
                f"required_tempos={settings.commit_cycle_length}, "
                f"commit_window=({window.commit_start} - {window.commit_stop})"
            )

            if tempos_since_last_commit < settings.commit_cycle_length:
                logger.debug("Not enough tempos passed. Skipping weight commit")
                continue

            if current_block not in window.commit_window:
                logger.debug("Not in commit window. Skipping weight commit")
                continue

            # Commit weights
            logger.info(
                f"Attempting to commit weights at block {current_block} for epoch starting at {app.state.current_epoch_start}"
            )

            weights_to_set = await get_weights(app, current_block)
            if not weights_to_set:
                logger.warning("No weights returned by get_latest_weights. Skipping commit for this cycle.")
                continue

            logger.info(f"Found {len(weights_to_set)} weights to set. Committing...")
            try:
                reveal_round = await commit_weights(app, weights_to_set)
                logger.info(f"Successfully committed weights. Expected reveal round: {reveal_round}")
                app.state.reveal_round = reveal_round
                app.state.last_commit_block = current_block
                logger.info(f"Successfully committed weights at block {current_block}")
                last_successful_commit_block = current_block
            except Exception as commit_exc:
                logger.error(f"Failed to commit weights: {commit_exc}")

        except Exception as e:
            logger.error(f"Error in periodic weight setting task outer loop: {e}", exc_info=True)


async def fetch_latest_metagraph_task(app, stop_event: asyncio.Event):
    stop_task = asyncio.create_task(stop_event.wait())
    timeout = settings.fetch_latest_metagraph_task_interval_seconds
    while not stop_event.is_set():
        new_block = None
        try:
            new_block = await app.state.bittensor_client.head.get()
        except Exception as e:
            logger.error(f"Error fetching latest block: {e}")
            await asyncio.wait([stop_task], timeout=timeout)
            continue

        if new_block is None or new_block.number is None:
            logger.warning(f"New block fetched is invalid: {new_block}. Retrying...")
            await asyncio.wait([stop_task], timeout=timeout)
            continue

        if app.state.latest_block is None or new_block.number != app.state.latest_block:
            try:
                await cache_metagraph(app, new_block)
                app.state.latest_block = new_block.number
                app.state.current_epoch_start = get_epoch_containing_block(new_block.number).start
                logger.info(f"Cached latest metagraph for block {new_block.number}")
            except Exception as e:
                logger.error(f"Error caching metagraph for block {new_block.number}: {e}")

        await asyncio.wait([stop_task], timeout=timeout)
