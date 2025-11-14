"""
Custom Prometheus controller with Bearer token authorization using Litestar Guards.
"""

import logging

from litestar import Response, get
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers import BaseRouteHandler
from litestar.status_codes import HTTP_200_OK
from prometheus_client import REGISTRY, generate_latest

from pylon._internal.common.settings import settings

logger = logging.getLogger(__name__)


def metrics_auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """
    Guard for /metrics endpoint - validates Bearer token.

    Raises:
        PermissionDeniedException: If PYLON_METRICS_TOKEN is not configured
        NotAuthorizedException: If Authorization header is missing or invalid
    """
    if not settings.pylon_metrics_token:
        logger.warning("Metrics endpoint accessed but PYLON_METRICS_TOKEN is not configured")
        raise PermissionDeniedException(detail="Metrics endpoint is not configured")

    auth_header = connection.headers.get("Authorization")
    if not auth_header:
        logger.warning("Metrics endpoint accessed without Authorization header")
        raise NotAuthorizedException(detail="Authorization header is required")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning("Metrics endpoint accessed with invalid Authorization format")
        raise NotAuthorizedException(detail="Invalid Authorization header format. Expected: Bearer <token>")

    token = parts[1]

    if token != settings.pylon_metrics_token:
        logger.warning("Metrics endpoint accessed with invalid token")
        raise NotAuthorizedException(detail="Invalid authorization token")


@get("/metrics", guards=[metrics_auth_guard])
async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    Protected by metrics_auth_guard - requires Bearer token matching PYLON_METRICS_TOKEN.
    """
    return Response(
        content=generate_latest(REGISTRY),
        status_code=HTTP_200_OK,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
