import asyncio
import time

import pytest
import pytest_asyncio

from pylon_client.client import PylonClient
from pylon_client.docker_manager import PylonDockerManager

PYLON_TEST_PORT = 8001


@pytest_asyncio.fixture
async def client():
    """
    Pytest fixture to initialize PylonClient and manage the Pylon Docker service.
    """
    client = PylonClient(port=PYLON_TEST_PORT)
    manager = PylonDockerManager(client=client)
    async with client, manager:
        yield client


@pytest.mark.asyncio
async def test_client_metagraph_caching(client: PylonClient):
    """
    Test metagraph caching by comparing querying time for multiple metagraph fetches not in cache vs cached metagraph fetches.
    """
    # get block for reference
    latest_block_resp = await client.get_latest_block()
    assert latest_block_resp and "block" in latest_block_resp, "Could not get latest block"
    latest_block = latest_block_resp["block"]

    block_range = 10
    block = latest_block - block_range

    # run 2 rounds of the same metagraph block range queries
    times = []
    for _ in range(2):
        start_time = time.monotonic()
        tasks = [client.get_metagraph(block - i) for i in range(block_range)]
        results = await asyncio.gather(*tasks)
        elapsed = time.monotonic() - start_time
        times.append(elapsed)

        for res in results:
            assert res is not None, "Metagraph response is None"
            assert res.neurons, f"Invalid metagraph response: {res.model_dump().keys()}"
            assert len(res.neurons) > 0, f"No neurons in metagraph response: {res.model_dump().keys()}"

    # the second round should be faster than the first due to caching
    assert times[1] * 2 < times[0], (
        f"Cache speed-up assertion failed: {times[1]:.2f}s not significantly faster than {times[0]:.2f}s"
    )
