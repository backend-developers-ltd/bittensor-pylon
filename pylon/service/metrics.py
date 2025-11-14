"""
Prometheus metrics for Bittensor Pylon service.

This module defines all domain-specific metrics for monitoring:
- Bittensor blockchain operations
- ApplyWeights background task
- API business logic errors
"""

import functools
import inspect
import logging
from collections.abc import Callable, Coroutine, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from time import perf_counter
from typing import TYPE_CHECKING, Any

from prometheus_client import Counter, Histogram

from pylon._internal.common.types import Hotkey, NetUid, RevealRound, Weight

if TYPE_CHECKING:
    from pylon.service.bittensor.client import AbstractBittensorClient

logger = logging.getLogger(__name__)


bittensor_operations_total = Counter(
    "pylon_bittensor_operations_total",
    "Total number of Bittensor blockchain operations",
    ["operation", "status", "client_type"],
)

bittensor_operation_duration = Histogram(
    "pylon_bittensor_operation_duration_seconds",
    "Duration of Bittensor blockchain operations in seconds",
    ["operation", "client_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

bittensor_errors_total = Counter(
    "pylon_bittensor_errors_total",
    "Total number of errors in Bittensor operations",
    ["operation", "exception", "client_type"],
)

bittensor_fallback_total = Counter(
    "pylon_bittensor_fallback_total",
    "Total number of archive client fallback events",
    ["reason", "operation"],
)

apply_weights_duration = Histogram(
    "pylon_apply_weights_duration_seconds",
    "Duration of apply weights job execution in seconds",
    ["mode", "status"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

apply_weights_jobs_total = Counter(
    "pylon_apply_weights_jobs_total",
    "Total number of apply weights jobs",
    ["mode", "status"],
)


class TrackedBittensorClient:
    """
    Proxy for AbstractBittensorClient that auto-tracks all operations.
    """

    def __init__(self, client: "AbstractBittensorClient") -> None:
        self._client = client
        self._client_type: str = getattr(client, "_client_type", "unknown")

    def _record_operation_metrics(self, operation: str, duration: float, exception_name: str | None = None) -> None:
        status = "error" if exception_name else "success"
        bittensor_operations_total.labels(
            operation=operation,
            status=status,
            client_type=self._client_type,
        ).inc()
        if exception_name:
            bittensor_errors_total.labels(
                operation=operation,
                exception=exception_name,
                client_type=self._client_type,
            ).inc()
        bittensor_operation_duration.labels(
            operation=operation,
            client_type=self._client_type,
        ).observe(duration)

    @contextmanager
    def _operation_span(self, operation: str) -> Generator[None, None, None]:
        start_time = perf_counter()
        try:
            yield
        except Exception as exc:
            self._record_operation_metrics(operation, perf_counter() - start_time, type(exc).__name__)
            raise
        self._record_operation_metrics(operation, perf_counter() - start_time)

    async def _track_async_operation(
        self, operation: str, method: Callable[..., Coroutine[Any, Any, Any]], *args: Any, **kwargs: Any
    ) -> Any:
        with self._operation_span(operation):
            return await method(*args, **kwargs)

    def _track_sync_operation(self, operation: str, method: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self._operation_span(operation):
            return method(*args, **kwargs)

    async def commit_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> RevealRound:
        _set_job_mode("commit")
        return await self._track_async_operation("commit_weights", self._client.commit_weights, netuid, weights)

    async def set_weights(self, netuid: NetUid, weights: dict[Hotkey, Weight]) -> None:
        _set_job_mode("set")
        return await self._track_async_operation("set_weights", self._client.set_weights, netuid, weights)

    def __getattr__(self, name: str) -> Any:
        """
        Proxy all other methods transparently.

        Async and sync callables are wrapped with tracking, other attributes pass through.
        """
        attr = getattr(self._client, name)

        if inspect.iscoroutinefunction(attr):

            async def tracked_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self._track_async_operation(name, attr, *args, **kwargs)

            return tracked_wrapper

        if callable(attr):

            def tracked_sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return self._track_sync_operation(name, attr, *args, **kwargs)

            return tracked_sync_wrapper

        return attr


class _JobContext:
    """Generic state holder for job metrics."""

    def __init__(self, duration_metric: Histogram, counter_metric: Counter) -> None:
        self.duration_metric: Histogram = duration_metric
        self.counter_metric: Counter = counter_metric
        self.mode: str = "unknown"
        self.status: str = "success"
        self._start_time: float = perf_counter()

    def finalize(self) -> None:
        duration = perf_counter() - self._start_time
        self.duration_metric.labels(mode=self.mode, status=self.status).observe(duration)
        self.counter_metric.labels(mode=self.mode, status=self.status).inc()


_current_job: ContextVar[_JobContext | None] = ContextVar(
    "current_job",
    default=None,
)


def _set_job_mode(mode: str) -> None:
    """Set the mode for the current job context (e.g., 'commit', 'set')."""
    job = _current_job.get()
    if job is not None:
        job.mode = mode


def _set_job_status(status: str) -> None:
    """Set the status for the current job context (e.g., 'tempo_expired')."""
    job = _current_job.get()
    if job is not None:
        job.status = status


def track_job(
    duration_metric: Histogram, counter_metric: Counter
) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    """
    Decorator factory that records job-level metrics.

    Args:
        duration_metric: Histogram metric for tracking job duration
        counter_metric: Counter metric for tracking job counts
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            job = _JobContext(duration_metric, counter_metric)
            token = _current_job.set(job)

            try:
                result = await func(*args, **kwargs)
                return result
            except TimeoutError:
                job.status = "timeout"
                raise
            except Exception:
                job.status = "error"
                raise
            finally:
                _current_job.reset(token)
                job.finalize()

        return wrapper

    return decorator
