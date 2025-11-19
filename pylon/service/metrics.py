"""
Prometheus metrics for Bittensor Pylon service.

This module defines all domain-specific metrics for monitoring:
- Bittensor blockchain operations
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from collections.abc import Coroutine as CoroutineType
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any, TypeVar, cast

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., CoroutineType[Any, Any, Any]])
R_co = TypeVar("R_co", covariant=True)


class MetricsConfigurationError(Exception):
    """Raised when metrics label configuration is invalid."""

    pass


class MetricsContext:
    """
    Context for tracking metrics during operation execution.

    Allows setting additional labels dynamically during operation execution
    that will be included in the final metrics recording.
    """

    def __init__(self, base_labels: dict[str, str]):
        self.base_labels = base_labels.copy()
        self.dynamic_labels: dict[str, str] = {}

    def set_label(self, key: str, value: str) -> None:
        """Set a dynamic label that will be included in metrics."""
        self.dynamic_labels[key] = value

    def get_all_labels(self) -> dict[str, str]:
        """Get all labels (base + dynamic) for metrics recording."""
        return {**self.base_labels, **self.dynamic_labels}


bittensor_operation_duration = Histogram(
    "pylon_bittensor_operation_duration_seconds",
    "Duration of Bittensor blockchain operations in seconds",
    ["operation", "status", "client_type", "netuid", "hotkey"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

bittensor_errors_total = Counter(
    "pylon_bittensor_errors_total",
    "Total number of errors in Bittensor operations",
    ["operation", "exception", "client_type", "netuid", "hotkey"],
)

bittensor_fallback_total = Counter(
    "pylon_bittensor_fallback_total",
    "Total number of archive client fallback events",
    ["reason", "operation", "hotkey"],
)

# ApplyWeights metrics
apply_weights_job_duration = Histogram(
    "pylon_apply_weights_job_duration_seconds",
    """Duration of entire ApplyWeights job execution (outer ``run_job`` wrapper).

    Labels:
        job_status: Business outcome set via ``MetricsContext`` ("completed", "tempo_expired", "failed", ...).
        netuid: Subnet identifier for multi-net deployments.
        hotkey: Wallet hotkey (ss58) used by the client submitting weights.
    """,
    ["job_status", "netuid", "hotkey"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1200.0),
)

apply_weights_job_errors = Counter(
    "pylon_apply_weights_job_errors_total",
    """Total number of errors raised by the ApplyWeights job wrapper.

    Labels:
        job_status: Business outcome tag that was set before the exception (e.g. "failed").
        netuid: Subnet identifier.
        hotkey: Wallet hotkey (ss58) used by the client submitting weights.
    """,
    ["job_status", "netuid", "hotkey"],
)

apply_weights_attempt_duration = Histogram(
    "pylon_apply_weights_attempt_duration_seconds",
    """Duration of individual `_apply_weights` attempts (inner business logic).

    Labels:
        operation: Name of the inner coroutine (``_apply_weights``).
        status: Outcome of the attempt ("success" / "error").
        netuid: Subnet identifier.
        hotkey: Wallet hotkey (ss58) used by the client submitting weights.
    """,
    ["operation", "status", "netuid", "hotkey"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

apply_weights_attempt_errors = Counter(
    "pylon_apply_weights_attempt_errors_total",
    """Total number of errors observed inside `_apply_weights`.

    Labels:
        operation: Name of the inner coroutine.
        netuid: Subnet identifier.
        hotkey: Wallet hotkey (ss58) used by the client submitting weights.
    """,
    ["operation", "netuid", "hotkey"],
)


def track_operation(
    duration_metric: Histogram,
    error_metric: Counter,
    operation_name: str | None = None,
    labels: dict[str, str] | None = None,
    *,
    inject_context: str | None = None,
):
    """
    Operation tracking decorator with explicit metrics context passing.

    This decorator:
    1. Extracts initial labels from method parameters/attributes
    2. Creates a MetricsContext and optionally injects it as a parameter
    3. Allows dynamic label setting during execution via the context
    4. Records metrics with all labels (initial + dynamic) when operation completes

    Args:
        duration_metric: Prometheus Histogram for operation duration
        error_metric: Prometheus Counter for operation errors
        operation_name: Custom operation name. If None, uses method name.
        labels: Label extraction with EXPLICIT prefixes:
            - "static:value" -> Static string "value"
            - "param:name" -> Extract from method parameter "name"
            - "attr:field" -> Extract from self.field attribute
        inject_context: Parameter name to inject MetricsContext into. If None, no injection.

    Examples:
        @track_operation(
            duration_metric=my_duration_histogram,
            error_metric=my_error_counter,
            labels={"client_type": "attr:_client_type"},
            inject_context="metrics"
        )
        async def apply_weights(self, mode: str, *, metrics: MetricsContext):
            # Set dynamic label during execution
            metrics.set_label("mode", mode)  # Will be included in final metrics

            if mode == "commit":
                metrics.set_label("operation_type", "commit_reveal")
            else:
                metrics.set_label("operation_type", "direct_set")

            # ... operation logic

        @track_operation(
            duration_metric=bittensor_operation_duration,
            error_metric=bittensor_errors_total,
            labels={
                "netuid": "param:netuid",
                "client_type": "attr:_client_type",
            },
            inject_context="ctx"
        )
        async def get_neurons(self, netuid: int, *, ctx: MetricsContext):
            # Can set additional context-specific labels
            ctx.set_label("cache_status", "miss" if not_in_cache else "hit")
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # We bind the original call to inspect parameters/attributes for label extraction.
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            self_obj = args[0] if args else None
            op_name = operation_name or func.__name__
            extracted_labels = _extract_labels(labels or {}, self_obj, bound_args.arguments)

            context = MetricsContext(extracted_labels)

            call_kwargs = dict(kwargs)
            if inject_context:
                if inject_context in call_kwargs:
                    raise ValueError(f"Parameter '{inject_context}' already exists in function call")
                call_kwargs[inject_context] = context

            async with _track_operation_context(op_name, context, duration_metric, error_metric):
                return await func(*args, **call_kwargs)  # type: ignore[misc]

        return cast(F, wrapper)

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


def _filter_labels_for_metric(metric: Histogram | Counter, labels: dict[str, str]) -> dict[str, str]:
    """
    Filter labels to only include those that the metric expects.

    Prometheus metrics have a fixed set of label names defined at creation time.
    This function filters the provided labels to only include those expected by the metric.
    """
    # Get the metric's expected label names
    expected_labels = metric._labelnames  # This is a tuple of expected label names

    # Filter to only include labels that the metric expects
    return {key: value for key, value in labels.items() if key in expected_labels}


@asynccontextmanager
async def _track_operation_context(
    operation: str, context: MetricsContext, duration_metric: Histogram, error_metric: Counter
):
    """Track operation with histogram + error counter using the provided metrics context."""
    start_time = perf_counter()
    status = "success"

    try:
        yield
    except Exception as exc:
        status = "error"
        exception_name = type(exc).__name__

        # Get final labels including any dynamically set ones
        final_labels = context.get_all_labels()

        # Filter labels to only those expected by the error metric
        error_labels = _filter_labels_for_metric(error_metric, final_labels)

        # Add required labels that might be missing
        error_labels_with_required = {"operation": operation, "exception": exception_name, **error_labels}

        # Record to error counter
        error_metric.labels(**error_labels_with_required).inc()

        raise
    finally:
        # Get final labels including any dynamically set ones
        final_labels = context.get_all_labels()

        # Filter labels to only those expected by the duration metric
        duration_labels = _filter_labels_for_metric(duration_metric, final_labels)

        # Add required labels that might be missing
        duration_labels_with_required = {"operation": operation, "status": status, **duration_labels}

        duration = perf_counter() - start_time
        duration_metric.labels(**duration_labels_with_required).observe(duration)
