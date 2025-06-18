import asyncio
import logging
from collections.abc import Callable
from functools import partial

from cachetools import TTLCache
from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig

from app.api import (
    block_hash,
    epoch_start,
    force_commit_weights,
    get_commitment_endpoint,
    get_commitments_endpoint,
    hyperparams,
    latest_block,
    latest_metagraph,
    metagraph,
    raw_weights,
    set_commitment_endpoint,
    set_weight,
    update_weight,
)
from app.bittensor_client import create_bittensor_client
from app.db import init_db
from app.settings import settings
from app.tasks import fetch_latest_hyperparams_task, fetch_latest_metagraph_task, set_weights_periodically_task

logger = logging.getLogger(__name__)


async def on_startup(app: Litestar, tasks_to_run: list[Callable]) -> None:
    logger.debug("Litestar app startup")
    await init_db()

    app.state.bittensor_client = await create_bittensor_client()
    await app.state.bittensor_client.__aenter__()

    app.state.metagraph_cache = TTLCache(maxsize=settings.metagraph_cache_maxsize, ttl=settings.metagraph_cache_ttl)
    app.state.latest_block: int | None = None
    app.state.current_epoch_start: int | None = None
    app.state.hyperparams = dict()

    app.state._stop_event = asyncio.Event()
    app.state._background_tasks: list[asyncio.Task] = []
    for task_func in tasks_to_run:
        task = asyncio.create_task(task_func(app, app.state._stop_event))
        app.state._background_tasks.append(task)

    # Log all registered routes
    logger.debug("Registered routes:")
    for route in app.routes:
        logger.debug(f"{route.path} -> {getattr(route, 'handler', None)}")


async def on_shutdown(app: Litestar) -> None:
    logger.debug("Litestar app shutdown")
    app.state._stop_event.set()
    await asyncio.gather(*app.state._background_tasks)
    await app.state.bittensor_client.__aexit__(None, None, None)


def create_app(tasks: list[Callable]) -> Litestar:
    """Creates a Litestar app with a specific set of background tasks."""
    return Litestar(
        route_handlers=[
            # Bittensor state
            latest_block,
            block_hash,
            metagraph,
            latest_metagraph,
            epoch_start,
            hyperparams,
            # Validator weights
            set_weight,
            raw_weights,
            update_weight,
            force_commit_weights,
            # Commitments
            get_commitment_endpoint,
            get_commitments_endpoint,
            set_commitment_endpoint,
        ],
        openapi_config=OpenAPIConfig(
            title="Bittensor Pylon API",
            version="1.0.0",
            description="REST API for the bittensor-pylon service.",
        ),
        on_startup=[partial(on_startup, tasks_to_run=tasks)],
        on_shutdown=[on_shutdown],
    )


defined_startup_tasks = [
    fetch_latest_hyperparams_task,
    fetch_latest_metagraph_task,
    set_weights_periodically_task,
]

app = create_app(tasks=defined_startup_tasks)
