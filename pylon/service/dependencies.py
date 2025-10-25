from litestar.datastructures import State

from pylon.service.bittensor.client import AbstractBittensorClient


async def bt_client(state: State) -> AbstractBittensorClient:
    return state.bittensor_client
