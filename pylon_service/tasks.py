import asyncio
import logging
from typing import Any, ClassVar

from turbobt import Bittensor, Block

from pylon_common.settings import settings
from pylon_service.bittensor_client import (
    cache_metagraph,
    commit_weights,
    fetch_last_weight_commit_block,
    get_weights,
)
from pylon_service.utils import CommitWindow, get_epoch_containing_block, hotkeys_to_uids

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
            new_block_obj = await app.state.bittensor_client.head.get()
        except Exception as e:
            logger.error(f"Error fetching latest block: {e}")
            await asyncio.wait([stop_task], timeout=timeout)
            continue

        if new_block_obj is None or new_block_obj.number is None:
            logger.warning(f"New block fetched is invalid: {new_block_obj}. Retrying...")
            await asyncio.wait([stop_task], timeout=timeout)
            continue

        new_block = new_block_obj.number

        if app.state.latest_block is None or new_block != app.state.latest_block:
            try:
                await cache_metagraph(app, block=new_block, block_hash=new_block_obj.hash)
                app.state.latest_block = new_block
                app.state.current_epoch_start = get_epoch_containing_block(new_block).start
                logger.info(f"Cached latest metagraph for block {new_block}")
            except Exception as e:
                logger.error(f"Error caching metagraph for block {new_block}: {e}")

        await asyncio.wait([stop_task], timeout=timeout)


class ApplyWeights:
    JOB_NAME: ClassVar[str] = "apply_weights"

    def __init__(self, client: Bittensor):
        self._client: Bittensor = client

    @classmethod
    async def schedule(cls, client: Bittensor, weights: dict[str, float]) -> "ApplyWeights":
        apply_weights = ApplyWeights(client)
        task = asyncio.create_task(apply_weights.run_job(weights), name=cls.JOB_NAME)
        task.add_done_callback(apply_weights._log_done)
        return apply_weights

    async def run_job(self, weights: dict[str, float]) -> None:
        async with self._client:
            latest_block = await self._client.head.get()
            if latest_block.number is None:
                raise RuntimeError("Latest block number not available (run_job)")

            tempo = get_epoch_containing_block(latest_block.number)
            initial_tempo_start = tempo.start

            retry_count = settings.weights_retry_attempts
            timeout = settings.weights_call_timeout_seconds
            async with asyncio.timeout(timeout):
                for retry_no in range(retry_count + 1):
                    try:
                        if not self._is_current_tempo(latest_block, initial_tempo_start):
                            logger.warning("Apply weights job task cancelled: tempo changed")
                            break
                        logger.info(f"apply weights {retry_no}")
                        await self._apply_weights(weights, latest_block)
                        break
                    except Exception as exc:
                        logger.error(
                            "Error executing %s: %s (retry %s)",
                            self.JOB_NAME,
                            exc,
                            retry_no,
                            exc_info=True,
                        )
                        await asyncio.sleep(settings.weights_retry_delay_seconds)

    def _is_current_tempo(self, latest_block: Block, initial_tempo_start: int) -> bool:
        if latest_block.number is None:
            raise RuntimeError("Latest block number not available (_is_current_tempo)")

        tempo = get_epoch_containing_block(latest_block.number)
        if tempo.start != initial_tempo_start:
            return False
        return True

    async def _fetch_hyperparams(self, block_hash: str) -> dict[str, Any]:
        subnet = self._client.subnet(settings.bittensor_netuid)
        hyperparams = await subnet.get_hyperparameters(block_hash=block_hash)
        if hyperparams is None:
            raise RuntimeError("Failed to fetch hyperparameters")
        return dict(hyperparams)

    async def _apply_weights(self, weights: dict[str, float], latest_block: Block) -> None:
        hyperparams = await self._fetch_hyperparams(latest_block.hash)
        commit_reveal_enabled = bool(hyperparams.get("commit_reveal_weights_enabled", False))
        # alternatively
        # commit_reveal_enabled = await self._client.subtensor.state.getStorage(
        #     "SubtensorModule.CommitRevealWeightsEnabled", settings.bittensor_netuid
        # )
        subnet = self._client.subnet(settings.bittensor_netuid)
        neurons = await subnet.list_neurons(block_hash=latest_block.hash)
        uid_weights, missing_hotkeys = hotkeys_to_uids(neurons, weights)
        if missing_hotkeys:
            logger.warning(f"Missing hotkeys while applying weights: {missing_hotkeys}")

        weights_api = self._client.subnet(settings.bittensor_netuid).weights
        if commit_reveal_enabled:
            logger.info("Commit weights (reveal enabled)")
            await weights_api.commit(uid_weights)
        else:
            logger.info("Set weights (reveal disabled)")
            await weights_api.set(uid_weights)

    def _log_done(self, job: asyncio.Task[None]) -> None:
        logger.info(f"Task finished {job}")
        try:
            job.result()
        except Exception as exc:  # noqa: BLE001
            logger.error("Exception in weights job: %s", exc, exc_info=True)
