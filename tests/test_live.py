import asyncio
import time

import pytest
import pytest_asyncio

from pylon_client.client import PylonClient
from pylon_client.docker_manager import PylonDockerManager
from pylon_service.settings import settings

PYLON_TEST_PORT = 8001


@pytest_asyncio.fixture
async def client(monkeypatch):
    """
    Pytest fixture to initialize PylonClient and manage the Pylon Docker service
    with validator mode enabled.
    """
    monkeypatch.setattr(settings, "am_i_a_validator", True)
    client = PylonClient(port=PYLON_TEST_PORT)
    manager = PylonDockerManager(client=client)
    async with client, manager:
        yield client


@pytest.mark.skip  # TODO: fix in CI
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


@pytest.mark.skip  # TODO: fix in CI
@pytest.mark.asyncio
async def test_weights_endpoints(client: PylonClient):
    """
    Tests the full lifecycle of setting, updating, and retrieving weights.
    """
    hotkey = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"  # Example hotkey
    initial_weight = 2.0
    delta = 3.5
    expected_final_weight = initial_weight + delta

    # Get the current epoch for verification
    latest_block_resp = await client.get_latest_block()
    assert latest_block_resp and "block" in latest_block_resp, "Could not get latest block"
    latest_block = latest_block_resp["block"]
    epoch_resp = await client.get_epoch(latest_block)
    assert epoch_resp, "Could not get epoch"
    epoch = epoch_resp.epoch_start

    # Set, update, and check the weight
    await set_and_check_weight(client, hotkey, initial_weight)
    await update_and_check_weight(client, hotkey, delta, expected_final_weight)
    await check_raw_weights(client, epoch, {hotkey: expected_final_weight})


async def set_and_check_weight(client, hotkey, value):
    resp = await client.set_weight(hotkey, value)
    assert resp and resp.get("weight") == value, f"Expected {hotkey} weight to be set to {value}"


async def update_and_check_weight(client, hotkey, value, expected):
    resp = await client.update_weight(hotkey, value)
    assert resp and resp.get("weight") == expected, f"expected {hotkey} weight to be updated to {expected}"


async def check_raw_weights(client, epoch: int | None, expected_dict):
    resp = await client.get_raw_weights(epoch)
    assert resp and "weights" in resp, "Invalid weights response: {resp}"
    # assert resp.get("epoch") == epoch
    weights_dict = resp.get("weights")
    assert weights_dict == expected_dict


async def set_and_check_hyperparam(client, param, value):
    await client.set_hyperparam(param, value)
    hyperparams = await client.get_hyperparams()
    assert hyperparams and hyperparams != {}, "No hyperparams found: {hyperparams}"
    assert hyperparams.get(param) == value, f"Expected {param} to be {value}"


# TODO: tubobt sim
# @pytest.mark.skip
# @pytest.mark.asyncio
# async def test_weights_setting_throughout_epochs(client: PylonClient):
#     """
#     Tests setting, updating, and retrieving weights via the PylonClient.
#     """
#     hotkey_1 = "hotkey_1"
#     hotkey_2 = "hotkey_2"
#     hotkey_3 = "hotkey_3"
#
#     set_and_check_hyperparam("tempo", 100)
#
#     with controller.pause_block(20):
#         await set_and_check_weight(hotkey_1, 10.0)
#         await set_and_check_weight(hotkey_2, 20.0)
#
#     with controller.pause_block(25):
#         await update_and_check_weight(hotkey_1, 1.0, 11.0)
#
#     with controller.pause_block(30):
#         await check_raw_weights(0, {hotkey_1: 11.0, hotkey_2: 20.0, hotkey_3: 0.0})
#
#     # after epoch pass
#     with controller.pause_block(101):
#         await set_and_check_weight(hotkey_2, 30.0)
#
#     with controller.pause_block(110):
#         # previous epoch weights
#         await check_raw_weights(0, {hotkey_1: 11.0, hotkey_2: 20.0, hotkey_3: 0.0})
#         # current epoch weights
#         await check_raw_weights(100, {hotkey_1: 11.0, hotkey_2: 20.0, hotkey_3: 30.0})
