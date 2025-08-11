import asyncio
import logging
from collections.abc import Callable
from functools import partial

from cachetools import TTLCache
from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig

from pylon_common.settings import settings
from pylon_service.api import (
    block_hash,
    epoch_start_endpoint,
    force_commit_weights_endpoint,
    get_commitment_endpoint,
    get_commitments_endpoint,
    get_hyperparams_endpoint,
    health_check,
    latest_block,
    latest_metagraph,
    latest_weights_endpoint,
    metagraph,
    set_commitment_endpoint,
    set_hyperparam_endpoint,
    set_weight_endpoint,
    set_weights_endpoint,
    update_weight_endpoint,
    weights_endpoint,
)
from pylon_service.bittensor_client import create_bittensor_client
from pylon_service.db import init_db
from pylon_service.sentry_config import init_sentry
from pylon_service.tasks import (
    fetch_latest_hyperparams_task,
    fetch_latest_metagraph_task,
    set_weights_periodically_task,
)

logger = logging.getLogger(__name__)


async def on_startup(app: Litestar, tasks_to_run: list[Callable]) -> None:
    logger.debug("Litestar app startup")
    await init_db()

    app.state.bittensor_client = await create_bittensor_client()
    await app.state.bittensor_client.__aenter__()

    app.state.metagraph_cache = TTLCache(maxsize=settings.metagraph_cache_maxsize, ttl=settings.metagraph_cache_ttl)
    app.state.latest_block = None
    app.state.current_epoch_start = None
    app.state.hyperparams = dict()

    # for tracking weight commits
    app.state.reveal_round = None
    app.state.last_commit_block = None

    # periodic tasks
    app.state._stop_event = asyncio.Event()
    app.state._background_tasks = []
    for task_func in tasks_to_run:
        task = asyncio.create_task(task_func(app, app.state._stop_event))
        app.state._background_tasks.append(task)

    logger.debug("Registered routes:")
    for route in app.routes:
        logger.debug(f"{route.path} -> {getattr(route, 'handler', None)}")

    logger.info("Env vars:")
    for key, value in settings.dict().items():
        logger.info(f"{key} = {value}")


async def on_shutdown(app: Litestar) -> None:
    logger.debug("Litestar app shutdown")
    app.state._stop_event.set()
    await asyncio.gather(*app.state._background_tasks)
    await app.state.bittensor_client.__aexit__(None, None, None)


def create_app(tasks: list[Callable]) -> Litestar:
    """Creates a Litestar app with a specific set of background tasks."""
    return Litestar(
        route_handlers=[
            health_check,
            # Bittensor state
            latest_block,
            block_hash,
            metagraph,
            latest_metagraph,
            epoch_start_endpoint,
            # Hyperparams
            get_hyperparams_endpoint,
            set_hyperparam_endpoint,
            # Validator weights
            set_weight_endpoint,
            set_weights_endpoint,
            latest_weights_endpoint,
            weights_endpoint,
            update_weight_endpoint,
            force_commit_weights_endpoint,
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

init_sentry()
app = create_app(tasks=defined_startup_tasks)
