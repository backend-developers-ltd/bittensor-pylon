from litestar.datastructures import State

from pylon.service.bittensor.client import AbstractBittensorClient


async def bt_client(state: State) -> AbstractBittensorClient:
    """
    Pre-instantiated bittensor client. All bittensor operations in the service shall be performed through this client.
    """
    return state.bittensor_client
