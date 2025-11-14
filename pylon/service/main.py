from litestar import Litestar
from litestar.di import Provide
from litestar.openapi.config import OpenAPIConfig
from litestar.plugins.prometheus import PrometheusConfig

from pylon._internal.common.settings import settings
from pylon.service import dependencies
from pylon.service.lifespans import bittensor_client
from pylon.service.prometheus_controller import metrics_endpoint
from pylon.service.routers import v1_router
from pylon.service.schema import PylonSchemaPlugin
from pylon.service.sentry_config import init_sentry


def create_app() -> Litestar:
    """Create a Litestar app"""
    # Configure Prometheus
    prometheus_config = PrometheusConfig(
        app_name="bittensor-pylon",
        prefix="pylon",
        group_path=True,  # Group metrics by path template to avoid cardinality explosion
    )

    return Litestar(
        route_handlers=[
            v1_router,
            metrics_endpoint,
        ],
        openapi_config=OpenAPIConfig(
            title="Bittensor Pylon API",
            version="0.1.0",
            description="REST API for the bittensor-pylon service",
        ),
        middleware=[prometheus_config.middleware],
        lifespan=[bittensor_client],
        dependencies={"bt_client": Provide(dependencies.bt_client, use_cache=True)},
        plugins=[PylonSchemaPlugin()],
        debug=settings.debug,
    )


init_sentry()
app = create_app()
