from litestar import Litestar
from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig

from pylon._internal.common.settings import settings
from pylon.service import dependencies
from pylon.service.lifespans import bittensor_client_pool
from pylon.service.routers import v1_router
from pylon.service.schema import PylonSchemaPlugin
from pylon.service.sentry_config import init_sentry


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
        lifespan=[bittensor_client_pool],
        dependencies={"bt_client_pool": Provide(dependencies.bt_client_pool_dep, use_cache=True)},
        plugins=[PylonSchemaPlugin()],
        debug=settings.debug,
    )


init_sentry()
app = create_app()
