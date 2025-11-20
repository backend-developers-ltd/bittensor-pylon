#!/usr/bin/env python3
"""
Smoke-test for Prometheus metrics exposed by the running Pylon service.

The script:
1. Calls API endpoints to trigger Bittensor client operations and an ApplyWeights job.
2. Fetches the /metrics endpoint.
3. Validates that key metrics increased.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import requests


def request_json(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    resp = requests.request(method, url, timeout=10, **kwargs)
    resp.raise_for_status()
    if not resp.content:
        return {}
    return resp.json()


LATEST_NEURONS_PATH = "/api/v1/neurons/latest"
SET_WEIGHTS_PATH = "/api/v1/subnet/weights"


def trigger_activity(base_url: str) -> None:
    print(f"Calling latest neurons via {base_url}{LATEST_NEURONS_PATH} …")
    latest = request_json("GET", f"{base_url}{LATEST_NEURONS_PATH}")
    print("Latest neurons response keys:", list(latest.keys()))

    payload = {"weights": {"demo_hotkey": 1.0}}
    print("Scheduling apply weights job …")
    ack = request_json(
        "PUT",
        f"{base_url}{SET_WEIGHTS_PATH}",
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    print("Scheduler response:", ack)


def fetch_metrics(base_url: str, wait_seconds: float) -> str:
    if wait_seconds:
        print(f"Waiting {wait_seconds:.1f}s for background job to finish …")
        time.sleep(wait_seconds)

    headers = {}
    token = os.environ.get("METRICS_TOKEN") or os.environ.get("PYLON_METRICS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(f"{base_url}/metrics", timeout=10, headers=headers or None)
    resp.raise_for_status()
    body = resp.text
    print("\n=== Metrics snippet ===")
    for line in body.splitlines():
        if line.startswith("pylon_"):
            print(line)
    return body


def first_metric_value(metrics_text: str, metric_prefix: str) -> float | None:
    """
    Return the value of the first metric line that starts with metric_prefix.
    """
    for line in metrics_text.splitlines():
        if line.startswith(metric_prefix):
            try:
                return float(line.rsplit(" ", 1)[-1])
            except ValueError:
                return None
    return None


def validate_metrics(metrics_text: str) -> None:
    core_metric = "pylon_bittensor_operations_total"

    value = first_metric_value(metrics_text, core_metric)
    if value is None or value <= 0.0:
        raise SystemExit(f"Validation failed:\n- No Bittensor operations were recorded. (metric='{core_metric}')")

    print("\nValidation passed ✅")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test Pylon Prometheus metrics.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running service (default: %(default)s)",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=2.0,
        help="Seconds to wait before scraping /metrics (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        trigger_activity(args.base_url)
        metrics_text = fetch_metrics(args.base_url, args.wait)
        validate_metrics(metrics_text)
    except requests.HTTPError as err:
        print(f"HTTP error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
