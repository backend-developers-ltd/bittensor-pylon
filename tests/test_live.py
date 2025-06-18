import asyncio
import time

import pytest
import pytest_asyncio

from app.settings import Settings
from pylon_client import PylonClient

PYLON_TEST_BASE_URL = "http://localhost"
PYLON_TEST_PORT = 8000


@pytest_asyncio.fixture(scope="function")
async def pylon_client_setup():
    """
    Pytest fixture to initialize PylonClient and manage the Pylon Docker service.
    """
    client = PylonClient(base_url=PYLON_TEST_BASE_URL, port=PYLON_TEST_PORT, timeout=30.0)
    container = None
    try:
        async with client as active_client:
            env_vars = Settings().model_dump()
            container = await active_client.start_pylon_service(
                env_vars=env_vars, image_name=env_vars["pylon_docker_image_name"]
            )
            yield active_client
    except Exception as e:
        pytest.fail(f"Pylon service setup failed: {e}")
    finally:
        if container:
            await client.stop_pylon_service(container)


@pytest.mark.asyncio
async def test_client_metagraph_caching(pylon_client_setup: PylonClient):
    """
    Test metagraph caching by comparing querying time for multiple metagraph fetches not in cache vs cached metagraph fetches.
    """
    client = pylon_client_setup

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
            assert res and res.neurons, f"Invalid metagraph response: {res.__keys__()}"
            assert len(res.neurons) > 0, f"No neurons in metagraph response: {res.__keys__()}"

    # the second round should be faster than the first due to caching
    assert times[1] * 2 < times[0], (
        f"Cache speed-up assertion failed: {times[1]:.2f}s not significantly faster than {times[0]:.2f}s"
    )


@pytest.mark.asyncio
async def test_client_weights(pylon_client_setup: PylonClient):
    """
    Tests setting, updating, and retrieving weights via the PylonClient.
    """
    client = pylon_client_setup
    test_hotkey = "hotkey_101"

    set_resp = await client.set_weight(test_hotkey, 42.0)
    assert set_resp and set_resp.get("weight") == 42.0, f"Expected {test_hotkey} weight to be set to 42.0"

    update_resp = await client.update_weight(test_hotkey, 8.0)
    assert update_resp and update_resp.get("weight") == 50.0, f"Expected {test_hotkey} weight to be updated to 50.0"

    get_resp = await client.get_raw_weights()
    assert get_resp and "weights" in get_resp, "Invalid weights response: {get_resp}"
    weights_dict = get_resp.get("weights")
    assert weights_dict[test_hotkey] == 50.0, f"Expected {test_hotkey} weight to be 50.0"
