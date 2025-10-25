import asyncio


async def wait_for_background_tasks(task_names: list[str] | None = None, timeout: float = 2.0) -> None:
    """
    Wait for background tasks to complete.

    Args:
        task_names: List of task names to wait for, or None to wait for all tasks
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If tasks don't complete within the timeout period
    """
    # Filter tasks based on names
    if task_names is None:
        tasks_to_wait = list(asyncio.all_tasks())
    else:
        tasks_to_wait = [task for task in asyncio.all_tasks() if task.get_name() in task_names]

    if not tasks_to_wait:
        return

    # Wait for all filtered tasks to complete
    done, pending = await asyncio.wait(tasks_to_wait, timeout=timeout)

    if pending:
        pending_names = [task.get_name() for task in pending]
        raise TimeoutError(f"Background tasks did not complete within {timeout}s: {pending_names}")
