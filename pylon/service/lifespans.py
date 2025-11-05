import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from bittensor_wallet import Wallet
from litestar import Litestar

from pylon._internal.common.settings import settings
from pylon.service.bittensor.client import BittensorClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def bittensor_client(app: Litestar) -> AsyncGenerator[None, None]:
    """
    Lifespan for litestar app that creates an instance of BittensorClient so that endpoints may reuse the connection.
    """
    logger.debug("Litestar app startup")
    wallet = Wallet(
        name=settings.bittensor_wallet_name,
        hotkey=settings.bittensor_wallet_hotkey_name,
        path=settings.bittensor_wallet_path,
    )
    async with BittensorClient(
        wallet=wallet,
        uri=settings.bittensor_network,
        archive_uri=settings.bittensor_archive_network,
        archive_blocks_cutoff=settings.bittensor_archive_blocks_cutoff,
    ) as client:
        app.state.bittensor_client = client
        yield
