from litestar import Litestar
from app.bittensor_client import create_bittensor_client
from app.api import latest_block, block_hash, metagraph, epoch, latest_metagraph
import logging
import asyncio

from app.tasks import fetch_latest_metagraph_task

from cachetools import TTLCache

logger = logging.getLogger(__name__)


METAGRAPH_CACHE_TTL = 600  # TODO: not 10 minutes
METAGRAPH_CACHE_MAXSIZE = 1000


async def on_startup(app: Litestar) -> None:
    logger.debug("Litestar app startup")
    app.state.bittensor_client = await create_bittensor_client()
    await app.state.bittensor_client.__aenter__()

    app.state._stop_event = asyncio.Event()
    app.state._bg_task = asyncio.create_task(fetch_latest_metagraph_task(app, app.state._stop_event))

    app.state.metagraph_cache = TTLCache(maxsize=METAGRAPH_CACHE_MAXSIZE, ttl=METAGRAPH_CACHE_TTL)
    app.state.latest_block = None

    # Log all registered routes for verification
    logger.debug("Registered routes:")
    for route in app.routes:
        logger.debug(f"{route.path} -> {getattr(route, 'handler', None)}")


async def on_shutdown(app: Litestar) -> None:
    logger.debug("Litestar app shutdown")
    app.state._stop_event.set()
    await app.state._bg_task
    await app.state.bittensor_client.__aexit__()


app = Litestar(
    route_handlers=[latest_block, block_hash, metagraph, epoch, latest_metagraph],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
)
