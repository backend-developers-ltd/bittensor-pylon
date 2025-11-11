import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from bittensor_wallet import Wallet
from litestar import Litestar
from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig

from pylon._internal.common.settings import settings
from pylon.service import dependencies
from pylon.service.bittensor.client import BittensorClient
from pylon.service.routers import v1_router
from pylon.service.schema import PylonSchemaPlugin
from pylon.service.sentry_config import init_sentry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def bittensor_client(app: Litestar) -> AsyncGenerator[None, None]:
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


def create_app() -> Litestar:
    """Create a Litestar app"""
    return Litestar(
        route_handlers=[
            v1_router,
        ],
        openapi_config=OpenAPIConfig(
            title="Bittensor Pylon API",
            version="0.1.0",
            description="REST API for the bittensor-pylon service",
        ),
        lifespan=[bittensor_client],
        dependencies={"bt_client": Provide(dependencies.bt_client, use_cache=True)},
        plugins=[PylonSchemaPlugin()],
        debug=settings.debug,
    )


init_sentry()
app = create_app()
