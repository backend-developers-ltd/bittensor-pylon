import asyncio
import logging
from collections.abc import Callable

from cachetools import TTLCache
from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig

from pylon._internal.common.settings import settings
from pylon.service.bittensor_client import create_bittensor_clients
from pylon.service.routers import v1_router
from pylon.service.sentry_config import init_sentry

logger = logging.getLogger(__name__)


async def on_startup(app: Litestar, tasks_to_run: list[Callable]) -> None:
    logger.debug("Litestar app startup")

    main_client, archive_client = await create_bittensor_clients()
    app.state.bittensor_client = main_client
    app.state.archive_bittensor_client = archive_client
    await app.state.bittensor_client.__aenter__()
    await app.state.archive_bittensor_client.__aenter__()

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
    await app.state.archive_bittensor_client.__aexit__(None, None, None)


def create_app_v2() -> Litestar:
    """Create a Litestar app with limited number of resources"""
    return Litestar(
        route_handlers=[
            v1_router,
        ],
        openapi_config=OpenAPIConfig(
            title="Bittensor Pylon API",
            version="2.0.0",
            description="REST API for the bittensor-pylon service",
        ),
    )


init_sentry()
app = create_app_v2()
