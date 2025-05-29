import asyncio
import logging

from cachetools import TTLCache
from litestar import Litestar

from app.api import block_hash, epoch_start, hyperparams, latest_block, latest_metagraph, metagraph
from app.bittensor_client import create_bittensor_client
from app.tasks import fetch_latest_hyperparams_task, fetch_latest_metagraph_task

logger = logging.getLogger(__name__)


METAGRAPH_CACHE_TTL = 600  # TODO: not 10 minutes
METAGRAPH_CACHE_MAXSIZE = 1000


async def on_startup(app: Litestar) -> None:
    logger.debug("Litestar app startup")
    app.state.bittensor_client = await create_bittensor_client()
    await app.state.bittensor_client.__aenter__()

    app.state.metagraph_cache = TTLCache(maxsize=METAGRAPH_CACHE_MAXSIZE, ttl=METAGRAPH_CACHE_TTL)
    app.state.latest_block: int | None = None
    app.state.current_epoch_start: int | None = None
    app.state.hyperparams = dict()

    app.state._stop_event = asyncio.Event()
    app.state._hyperparams_task = asyncio.create_task(fetch_latest_hyperparams_task(app, app.state._stop_event))
    app.state._metagraph_task = asyncio.create_task(fetch_latest_metagraph_task(app, app.state._stop_event))

    # Log all registered routes for verification
    logger.debug("Registered routes:")
    for route in app.routes:
        logger.debug(f"{route.path} -> {getattr(route, 'handler', None)}")


async def on_shutdown(app: Litestar) -> None:
    logger.debug("Litestar app shutdown")
    app.state._stop_event.set()
    await app.state._metagraph_task
    await app.state._hyperparams_task
    await app.state.bittensor_client.__aexit__(None, None, None)


app = Litestar(
    route_handlers=[latest_block, block_hash, metagraph, latest_metagraph, epoch_start, hyperparams],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
)
