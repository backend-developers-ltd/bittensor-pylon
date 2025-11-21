"""
Custom Prometheus controller with Bearer token authorization using Litestar Guards.

Uses Litestar's built-in PrometheusController with custom authentication guard
instead of implementing a custom endpoint from scratch.
"""

import logging
import secrets

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.handlers import BaseRouteHandler
from litestar.plugins.prometheus.controller import PrometheusController

from pylon._internal.common.settings import settings

logger = logging.getLogger(__name__)


def metrics_auth_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """
    Guard for /metrics endpoint - validates Bearer token.

    Raises:
        PermissionDeniedException: If PYLON_METRICS_TOKEN is not configured
        NotAuthorizedException: If Authorization header is missing or invalid
    """
    if not settings.metrics_token:
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

    if not secrets.compare_digest(token, settings.metrics_token):
        logger.warning("Metrics endpoint accessed with invalid token")
        raise NotAuthorizedException(detail="Invalid authorization token")


class AuthenticatedPrometheusController(PrometheusController):
    """
    PrometheusController with Bearer token authentication.
    """

    guards = [metrics_auth_guard]
