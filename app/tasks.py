import asyncio
import logging
from app.bittensor_client import cache_metagraph

FETCH_LATEST_INTERVAL_SECONDS = 10

logger = logging.getLogger(__name__)


async def fetch_latest_metagraph_task(app, stop_event: asyncio.Event):
    client = app.state.bittensor_client
    logger.info(f"Starting background latest metagraph fetcher every {FETCH_LATEST_INTERVAL_SECONDS} seconds.")
    stop_task = asyncio.create_task(stop_event.wait())
    while not stop_event.is_set():
        try:
            async with client.head as new_block:
                if app.state.latest_block is None or new_block.number != app.state.latest_block:
                    await cache_metagraph(app, client, new_block)
                    app.state.latest_block = new_block.number
                    logger.info(f"Cached latest metagraph for block {new_block.number}")
        except Exception as e:
            logger.error(f"Error fetching latest metagraph: {e}")
        await asyncio.wait([stop_task], timeout=FETCH_LATEST_INTERVAL_SECONDS)
