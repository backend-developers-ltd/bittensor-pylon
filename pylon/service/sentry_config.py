import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.litestar import LitestarIntegration

from pylon._internal.common.settings import settings


def init_sentry() -> None:
    """Initialize Sentry if DSN is configured."""
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        integrations=[
            LitestarIntegration(),
            AsyncioIntegration(),
        ],
    )
