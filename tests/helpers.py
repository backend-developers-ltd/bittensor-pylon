import asyncio
from collections.abc import Iterable
from unittest.mock import MagicMock

from bittensor_wallet import Wallet


def make_mock_wallet(hotkey_ss58: str = "test_hotkey") -> Wallet:
    """
    Create a mock Wallet object for testing.

    Args:
        hotkey_ss58: The SS58 address to use for the hotkey

    Returns:
        A MagicMock configured to behave like a Wallet
    """
    mock_wallet = MagicMock(spec=Wallet)
    mock_wallet.hotkey.ss58_address = hotkey_ss58
    return mock_wallet


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
