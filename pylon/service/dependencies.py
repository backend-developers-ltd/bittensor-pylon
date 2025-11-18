from collections.abc import AsyncGenerator
from typing import TypeVar

from litestar.datastructures import State
from litestar.exceptions import NotFoundException

from pylon._internal.common.types import IdentityName
from pylon.service.bittensor.client import AbstractBittensorClient
from pylon.service.bittensor.pool import BittensorClientPool
from pylon.service.identities import Identity, identities

BtClient = TypeVar("BtClient", bound=AbstractBittensorClient)


async def bt_client_pool_dep(state: State) -> BittensorClientPool:
    """
    Pool of bittensor clients. Every client used in the service should be taken from the pool to maintain and reuse
    connections.
    """
    return state.bittensor_client_pool


async def identity_dep(identity_name: IdentityName) -> Identity:
    # TODO: When authentication is added, identity will be fetched from the session. A Guard will guarantee that the
    #   data from identity in the session matches the data in an url.
    if identity_ := identities.get(identity_name):
        return identity_
    raise NotFoundException(f"Identity '{identity_name}' not found")


async def bt_client_identity_dep(
    bt_client_pool: BittensorClientPool[BtClient], identity: Identity
) -> AsyncGenerator[BtClient]:
    async with bt_client_pool.acquire(wallet=identity.wallet) as client:
        yield client


async def bt_client_open_access_dep(bt_client_pool: BittensorClientPool[BtClient]) -> AsyncGenerator[BtClient]:
    async with bt_client_pool.acquire(wallet=None) as client:
        yield client
