import functools
import logging
import secrets

from litestar import Request, Response, get, post, put
from turbobt import Bittensor

from pylon._internal.common.constants import (
    ENDPOINT_CERTIFICATES,
    ENDPOINT_CERTIFICATES_HOTKEY,
    ENDPOINT_CERTIFICATES_SELF,
    ENDPOINT_SUBNET_WEIGHTS,
)
from pylon._internal.common.models import (
    GenerateCertificateKeypairRequest,
    SetWeightsRequest,
)
from pylon._internal.common.settings import settings
from pylon.service.bittensor_client import (
    generate_certificate_keypair,
    get_bt_wallet,
    get_certificate,
    get_certificates,
)
from pylon.service.tasks import ApplyWeights

logger = logging.getLogger(__name__)


def token_required(func):
    """Decorator to restrict endpoint access for requests having proper token set in headers.

    Uses standard HTTP Authorization header with Bearer scheme.
    """

    @functools.wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        expected_token = settings.auth_token
        if not expected_token:
            return Response(status_code=500, content={"detail": "Token auth not configured"})

        auth_header = request.headers.get("Authorization")

        if auth_header is None:
            return Response(
                status_code=401,
                content={"detail": "Auth token required"},
            )

        # Parse "Bearer <token>" scheme (case-insensitive for scheme)
        parts = auth_header.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Invalid authorization header format for %s", func.__name__)
            return Response({"detail": "Invalid auth token"}, status_code=401)

        provided_token = parts[1].strip()
        if not provided_token or not secrets.compare_digest(provided_token, expected_token):
            logger.warning("Invalid authorization token for %s", func.__name__)
            return Response({"detail": "Invalid auth token"}, status_code=401)

        return await func(request, *args, **kwargs)

    return wrapper


def safe_endpoint(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            logger.info(f"{func.__name__}/ hit with: {kwargs.get('data', None)}")
            return await func(*args, **kwargs)
        except Exception as e:
            error_message = f"Error in endpoint {func.__name__}: {e}"
            logger.error(error_message)
            return Response(status_code=500, content={"detail": error_message})

    return wrapper


@put(ENDPOINT_SUBNET_WEIGHTS)
@token_required
@safe_endpoint
async def put_weights_endpoint(request: Request, data: SetWeightsRequest) -> Response:
    """
    Set multiple hotkeys' weights for the current epoch in a single transaction.
    (access validated by token in http headers)
    """
    client = Bittensor(wallet=get_bt_wallet(settings), uri=settings.bittensor_network)
    await ApplyWeights.schedule(client, data.weights)

    return Response(
        {
            "detail": "weights update scheduled",
            "count": len(data.weights),
        },
        status_code=200,
    )


@get(ENDPOINT_CERTIFICATES)
@safe_endpoint
async def get_certificates_endpoint(request: Request) -> Response:
    """
    Get all certificates for the subnet.
    """
    certificates = await get_certificates(request.app)

    return Response(certificates, status_code=200)


@get(ENDPOINT_CERTIFICATES_HOTKEY)
@safe_endpoint
async def get_certificate_endpoint(request: Request, hotkey: str) -> Response:
    """
    Get a specific certificate for a hotkey.
    """
    certificate = await get_certificate(request.app, hotkey)
    if certificate is None:
        return Response({"detail": "Certificate not found or error fetching."}, status_code=404)

    return Response(certificate, status_code=200)


@get(ENDPOINT_CERTIFICATES_SELF)
@safe_endpoint
async def get_own_certificate_endpoint(request: Request) -> Response:
    """
    Get a certificate for the app's wallet.
    """
    certificate = await get_certificate(request.app)
    if certificate is None:
        return Response({"detail": "Certificate not found or error fetching."}, status_code=404)

    return Response(certificate, status_code=200)


@post(ENDPOINT_CERTIFICATES_SELF)
@safe_endpoint
async def generate_certificate_keypair_endpoint(request: Request, data: GenerateCertificateKeypairRequest) -> Response:
    """
    Generate a certificate keypair for the app's wallet.
    """
    certificate_keypair = await generate_certificate_keypair(request.app, algorithm=data.algorithm)
    if certificate_keypair is None:
        return Response({"detail": "Could not generate certificate pair."}, status_code=400)

    return Response(certificate_keypair, status_code=201)
