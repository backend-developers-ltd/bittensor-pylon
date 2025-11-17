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
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from contextvars import ContextVar
from time import perf_counter
from typing import TypeVar

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

R = TypeVar("R")  # For return types


class MetricsConfigurationError(Exception):
    """Raised when metrics label configuration is invalid."""

    pass


bittensor_operation_duration = Histogram(
    "pylon_bittensor_operation_duration_seconds",
    "Duration of Bittensor blockchain operations in seconds",
    ["operation", "status", "client_type", "netuid"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

bittensor_errors_total = Counter(
    "pylon_bittensor_errors_total",
    "Total number of errors in Bittensor operations",
    ["operation", "exception", "client_type", "netuid"],
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


def track_operation(
    duration_metric: Histogram,
    error_metric: Counter,
    operation_name: str | None = None, 
    labels: dict[str, str] | None = None
):
    """
    Operation tracking decorator.

    Args:
        operation_name: Custom operation name. If None, uses method name.
        labels: Label extraction with EXPLICIT prefixes:
            - "static:value" -> Static string "value"
            - "param:name" -> Extract from method parameter "name"
            - "attr:field" -> Extract from self.field attribute

    Examples:
        @track_operation()
        async def get_latest_block(self):
            # Only operation="get_latest_block"

        @track_operation(labels={
            "netuid": "param:netuid",           # FROM method parameter netuid
            "client_type": "attr:_client_type", # FROM self._client_type
            "operation_type": "static:query"    # STATIC string "query"
        })
        async def get_neurons(self, netuid: int):
            # EXPLICIT: operation="get_neurons", netuid="12", client_type="main", operation_type="query"
    """

    def decorator(func: Callable[..., Coroutine[None, None, R]]) -> Callable[..., Coroutine[None, None, R]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> R:
            # Get method signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Extract self object
            self_obj = args[0] if args else None

            # Determine operation name
            op_name = operation_name or func.__name__

            # Extract labels
            extracted_labels = _extract_labels(labels or {}, self_obj, bound_args.arguments)

            # Track the operation with specific metrics
            async with _track_operation_context(op_name, extracted_labels, duration_metric, error_metric):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def _extract_labels(
    label_config: dict[str, str], self_obj: object | None, method_params: dict[str, object]
) -> dict[str, str]:
    """Extract labels with strict validation, raising exceptions on misconfiguration.

    Raises:
        MetricsConfigurationError: When label configuration is invalid or references missing attributes/parameters.
    """
    extracted = {}

    for label_name, source_spec in label_config.items():
        if not isinstance(source_spec, str) or ":" not in source_spec:
            raise MetricsConfigurationError(f"Label '{label_name}' must use explicit prefix format: 'type:value'")

        prefix, source = source_spec.split(":", 1)

        if prefix == "static":
            # Static string value
            value = source

        elif prefix == "param":
            # Extract from method parameter
            if source not in method_params:
                raise MetricsConfigurationError(
                    f"Parameter '{source}' not found in method signature for label '{label_name}'"
                )
            value = method_params[source]

        elif prefix == "attr":
            # Extract from self attribute
            if self_obj is None:
                raise MetricsConfigurationError(
                    f"Cannot extract attribute '{source}' for label '{label_name}' - no self object"
                )
            if not hasattr(self_obj, source):
                raise MetricsConfigurationError(
                    f"Attribute '{source}' not found on {type(self_obj).__name__} for label '{label_name}'"
                )
            value = getattr(self_obj, source)

        else:
            raise MetricsConfigurationError(
                f"Unknown label prefix '{prefix}' for label '{label_name}'. Use: static, param, or attr"
            )

        extracted[label_name] = str(value) if value is not None else "unknown"

    return extracted


@asynccontextmanager
async def _track_operation_context(operation: str, labels: dict[str, str], duration_metric: Histogram, error_metric: Counter):
    """Track operation with histogram + error counter."""
    start_time = perf_counter()
    status = "success"

    try:
        yield
    except Exception as exc:
        status = "error"
        exception_name = type(exc).__name__

        # Record to error counter
        error_metric.labels(operation=operation, exception=exception_name, **labels).inc()

        raise
    finally:
        duration = perf_counter() - start_time
        duration_metric.labels(operation=operation, status=status, **labels).observe(duration)


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
) -> Callable[[Callable[..., Coroutine[None, None, R]]], Callable[..., Coroutine[None, None, R]]]:
    """
    Decorator factory that records job-level metrics.

    Args:
        duration_metric: Histogram metric for tracking job duration
        counter_metric: Counter metric for tracking job counts
    """

    def decorator(func: Callable[..., Coroutine[None, None, R]]) -> Callable[..., Coroutine[None, None, R]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> R:
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
