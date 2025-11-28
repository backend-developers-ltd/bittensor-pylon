import asyncio
from collections.abc import Callable, Iterable
from typing import Any


async def wait_for_background_tasks(tasks_to_wait: Iterable[asyncio.Task], timeout: float = 2.0) -> None:
    """
    Wait for background tasks to complete.

    Args:
        tasks_to_wait: List of tasks to wait for
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If tasks don't complete within the timeout period
    """
    if not tasks_to_wait:
        return

    # Wait for all filtered tasks to complete
    done, pending = await asyncio.wait(tasks_to_wait, timeout=timeout)

    if pending:
        pending_names = [task.get_name() for task in pending]
        raise TimeoutError(f"Background tasks did not complete within {timeout}s: {pending_names}")


async def wait_until(func: Callable[[], Any], timeout: float = 2.0, sleep_interval: float = 0.1) -> None:
    async with asyncio.timeout(timeout):
        while not func():
            await asyncio.sleep(sleep_interval)
