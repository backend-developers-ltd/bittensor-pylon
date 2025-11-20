import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar

from pylon._internal.common.settings import settings
from pylon.service.bittensor.pool import BittensorClientPool

logger = logging.getLogger(__name__)


@asynccontextmanager
async def bittensor_client_pool(app: Litestar) -> AsyncGenerator[None, None]:
    """
    Lifespan for litestar app that creates an instance of BittensorClientPool so that endpoints may reuse connections.
    """
    logger.debug("Initializing bittensor client pool.")
    async with BittensorClientPool(
        uri=settings.bittensor_network,
        archive_uri=settings.bittensor_archive_network,
        archive_blocks_cutoff=settings.bittensor_archive_blocks_cutoff,
    ) as pool:
        app.state.bittensor_client_pool = pool
        yield
