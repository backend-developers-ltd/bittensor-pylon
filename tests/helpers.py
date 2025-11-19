import asyncio
from collections.abc import Iterable


class StubHotkey:
    def __init__(self, ss58_address: str = "test_hotkey") -> None:
        self.ss58_address = ss58_address


class StubWallet:
    def __init__(self, hotkey_ss58: str = "test_hotkey") -> None:
        self.hotkey = StubHotkey(hotkey_ss58)


def make_stub_wallet(hotkey_ss58: str = "test_hotkey") -> StubWallet:
    return StubWallet(hotkey_ss58)


async def wait_for_background_tasks(tasks_to_wait: Iterable[asyncio.Task] | None, timeout: float = 2.0) -> None:
    """
    Wait for background tasks to complete.

    Args:
        tasks_to_wait: List of tasks to wait for, or None to wait for ApplyWeights.tasks_running
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If tasks don't complete within the timeout period
    """
    if tasks_to_wait is None:
        # Import here to avoid circular imports
        from pylon.service.tasks import ApplyWeights

        tasks_to_wait = list(ApplyWeights.tasks_running)

    if not tasks_to_wait:
        return

    # Wait for all filtered tasks to complete
    done, pending = await asyncio.wait(tasks_to_wait, timeout=timeout)

    if pending:
        pending_names = [task.get_name() for task in pending]
        raise TimeoutError(f"Background tasks did not complete within {timeout}s: {pending_names}")
