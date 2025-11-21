import asyncio
import logging
from typing import ClassVar, Self

from pylon._internal.common.models import Block, CommitReveal
from pylon._internal.common.settings import settings
from pylon._internal.common.types import Hotkey, Weight
from pylon.service.bittensor.client import AbstractBittensorClient
from pylon.service.metrics import (
    MetricsContext,
    apply_weights_attempt_duration,
    apply_weights_job_duration,
    track_operation,
)
from pylon.service.utils import get_epoch_containing_block

logger = logging.getLogger(__name__)


class ApplyWeights:
    JOB_NAME: ClassVar[str] = "apply_weights"
    tasks_running = set()

    def __init__(self, client: AbstractBittensorClient):
        self._client: AbstractBittensorClient = client
        self._hotkey_ss58: str = client.wallet.hotkey.ss58_address
        self._netuid: str = str(settings.bittensor_netuid)

    @classmethod
    async def schedule(cls, client: AbstractBittensorClient, weights: dict[Hotkey, Weight]) -> Self:
        apply_weights = cls(client)
        task = asyncio.create_task(apply_weights.run_job(weights), name=cls.JOB_NAME)
        cls.tasks_running.add(task)
        task.add_done_callback(apply_weights._log_done)
        return apply_weights

    @track_operation(
        duration_metric=apply_weights_job_duration,
        labels={
            "netuid": "attr:_netuid",
            "hotkey": "attr:_hotkey_ss58",
        },
        inject_context="job_metrics",
    )
    async def run_job(
        self,
        weights: dict[Hotkey, Weight],
        *,
        job_metrics: MetricsContext | None = None,
    ) -> None:
        start_block = await self._client.get_latest_block()

        tempo = get_epoch_containing_block(start_block.number)
        initial_tempo = tempo

        if job_metrics:
            job_metrics.set_label("job_status", "running")

        retry_count = settings.weights_retry_attempts
        next_sleep_seconds = settings.weights_retry_delay_seconds
        max_sleep_seconds = next_sleep_seconds * 10

        for retry_no in range(retry_count + 1):
            latest_block = await self._client.get_latest_block()
            if latest_block.number > initial_tempo.end:
                if job_metrics:
                    job_metrics.set_label("job_status", "tempo_expired")
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
                if job_metrics:
                    job_metrics.set_label("attempt", str(retry_no))

                await asyncio.wait_for(self._apply_weights(weights, latest_block), 120)
                if job_metrics:
                    job_metrics.set_label("job_status", "completed")
                return
            except Exception as exc:
                logger.error(
                    "Error executing %s: %s (retry %s)",
                    self.JOB_NAME,
                    exc,
                    retry_no,
                    exc_info=True,
                )
                if retry_no == retry_count:
                    if job_metrics:
                        job_metrics.set_label("job_status", "failed")
                    raise
                logger.info(f"Sleeping for {next_sleep_seconds} seconds before retrying...")
                await asyncio.sleep(next_sleep_seconds)
                next_sleep_seconds = min(next_sleep_seconds * 2, max_sleep_seconds)

    @track_operation(
        duration_metric=apply_weights_attempt_duration,
        labels={
            "netuid": "attr:_netuid",
            "hotkey": "attr:_hotkey_ss58",
        },
    )
    async def _apply_weights(
        self,
        weights: dict[Hotkey, Weight],
        latest_block: Block,
    ) -> None:
        hyperparams = await self._client.get_hyperparams(settings.bittensor_netuid, latest_block)
        if hyperparams is None:
            raise RuntimeError("Failed to fetch hyperparameters")
        commit_reveal_enabled = hyperparams.commit_reveal_weights_enabled

        if commit_reveal_enabled and commit_reveal_enabled != CommitReveal.DISABLED:
            logger.info(f"Commit weights (reveal enabled: {commit_reveal_enabled})")
            await self._client.commit_weights(settings.bittensor_netuid, weights)
        else:
            logger.info("Set weights (reveal disabled)")
            await self._client.set_weights(settings.bittensor_netuid, weights)

    def _log_done(self, job: asyncio.Task[None]) -> None:
        logger.info(f"Task finished {job}")
        self.tasks_running.discard(job)
        try:
            job.result()
        except Exception as exc:  # noqa: BLE001
            logger.error("Exception in weights job: %s", exc, exc_info=True)
