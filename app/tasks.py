import asyncio
import logging

from app.bittensor_client import cache_metagraph
from app.settings import settings

FETCH_LATEST_INTERVAL_SECONDS = 10
FETCH_HYPERPARAMS_INTERVAL_SECONDS = 60
logger = logging.getLogger(__name__)


async def fetch_latest_hyperparams_task(app, stop_event: asyncio.Event):
    """
    Periodically fetch and cache subnet hyperparameters in app.state.hyperparams as a dict.
    """
    stop_task = asyncio.create_task(stop_event.wait())
    while not stop_event.is_set():
        try:
            await fetch_hyperparams(app)
        except Exception as e:
            logger.error(f"Failed to fetch subnet hyperparameters: {e}", exc_info=True)
        await asyncio.wait([stop_task], timeout=FETCH_HYPERPARAMS_INTERVAL_SECONDS)


async def fetch_hyperparams(app):
    subnet = app.state.bittensor_client.subnet(settings.bittensor_netuid)
    new_hyperparams = await subnet.get_hyperparameters()
    current_hyperparams = app.state.hyperparams
    for k, v in new_hyperparams.items():
        old_v = current_hyperparams.get(k, None)
        if old_v != v:
            logger.debug(f"Subnet hyperparame update: {k}: {old_v} -> {v}")
            app.state.hyperparams[k] = v


async def fetch_latest_metagraph_task(app, stop_event: asyncio.Event):
    stop_task = asyncio.create_task(stop_event.wait())
    while not stop_event.is_set():
        try:
            new_block = await app.state.bittensor_client.head.get()
            if app.state.latest_block is None or new_block.number != app.state.latest_block:
                await cache_metagraph(app, new_block)
                app.state.latest_block = new_block.number
                logger.info(f"Cached latest metagraph for block {new_block.number}")
        except Exception as e:
            logger.error(f"Error fetching latest metagraph: {e}", exc_info=True)
        await asyncio.wait([stop_task], timeout=FETCH_LATEST_INTERVAL_SECONDS)
