import asyncio
import logging
from typing import Any, ClassVar

from turbobt import Bittensor, Block

from pylon_common.settings import settings
from pylon_service.utils import get_epoch_containing_block, hotkeys_to_uids

logger = logging.getLogger(__name__)


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

    async def get_current_block(self):
        while True:
            try:
                latest_block = await self._client.head.get()
                assert latest_block is not None
                return latest_block
            except Exception as e:
                logger.error(f"Error fetching latest block: {e}")
                await asyncio.sleep(settings.weights_retry_delay_seconds)
                continue

    async def run_job(self, weights: dict[str, float]) -> None:
        async with self._client:
            start_block = await self.get_current_block()

            tempo = get_epoch_containing_block(start_block.number)
            initial_tempo = tempo

            retry_count = settings.weights_retry_attempts
            next_sleep_seconds = settings.weights_retry_delay_seconds
            max_sleep_seconds = next_sleep_seconds * 10
            for retry_no in range(retry_count + 1):
                latest_block = await self.get_current_block()
                if latest_block.number > initial_tempo.end:
                    logger.error(
                        f"Apply weights job task cancelled: tempo ended "
                        f"({latest_block.number} > {initial_tempo.end}, {start_block.number=})"
                    )
                    return
                logger.info(
                    f"apply weights {retry_no}, {latest_block.number=}, "
                    f"still got {initial_tempo.end - latest_block.number} blocks left to go."
                )
                try:
                    await asyncio.wait_for(self._apply_weights(weights, latest_block), 120)
                    return
                except Exception as exc:
                    logger.error(
                        "Error executing %s: %s (retry %s)",
                        self.JOB_NAME,
                        exc,
                        retry_no,
                        exc_info=True,
                    )
                    logger.info(f"Sleeping for {next_sleep_seconds} seconds before retrying...")
                    await asyncio.sleep(next_sleep_seconds)
                    next_sleep_seconds = min(next_sleep_seconds * 2, max_sleep_seconds)

    def _is_current_tempo(self, latest_block: Block, initial_tempo_start: int) -> bool:
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
