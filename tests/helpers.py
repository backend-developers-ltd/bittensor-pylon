import asyncio
from collections.abc import Callable, Iterable
from enum import StrEnum
from typing import Any, NamedTuple


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


class LockTrace(NamedTuple):
    class Action(StrEnum):
        ENTERED = "entered"
        ACQUIRED = "acquired"
        RELEASED = "released"

    task_name: str
    action: Action


class TracingLock(asyncio.Lock):
    """
    Lock that traces history of lock acquisition events.
    Also supports additional testing capacity of releasing the control to the event loop
    just after the lock acquisition.
    """

    def __init__(self, return_control: bool = False):
        super().__init__()
        self.trace: list[LockTrace] = []
        self.return_control = return_control

    def add_trace(self, action: LockTrace.Action):
        task = asyncio.current_task()
        task_name = task.get_name() if task is not None else ""
        self.trace.append(LockTrace(task_name=task_name, action=action))

    async def acquire(self):
        self.add_trace(LockTrace.Action.ENTERED)
        ret = await super().acquire()
        self.add_trace(LockTrace.Action.ACQUIRED)
        if self.return_control:
            await asyncio.sleep(0)
        return ret

    def release(self):
        self.add_trace(LockTrace.Action.RELEASED)
        return super().release()
