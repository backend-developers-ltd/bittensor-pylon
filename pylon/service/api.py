import functools
import logging

from litestar import Request, Response, get, post, put
from turbobt import Bittensor

from pylon._internal.common.endpoints import Endpoint
from pylon._internal.common.requests import (
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


@put(Endpoint.SUBNET_WEIGHTS)
@safe_endpoint
async def put_weights_endpoint(request: Request, data: SetWeightsRequest) -> Response:
    """
    Set multiple hotkeys' weights for the current epoch in a single transaction.
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


@get(Endpoint.CERTIFICATES)
@safe_endpoint
async def get_certificates_endpoint(request: Request) -> Response:
    """
    Get all certificates for the subnet.
    """
    certificates = await get_certificates(request.app)

    return Response(certificates, status_code=200)


@get(Endpoint.CERTIFICATES_HOTKEY)
@safe_endpoint
async def get_certificate_endpoint(request: Request, hotkey: str) -> Response:
    """
    Get a specific certificate for a hotkey.
    """
    certificate = await get_certificate(request.app, hotkey)
    if certificate is None:
        return Response({"detail": "Certificate not found or error fetching."}, status_code=404)

    return Response(certificate, status_code=200)


@get(Endpoint.CERTIFICATES_SELF)
@safe_endpoint
async def get_own_certificate_endpoint(request: Request) -> Response:
    """
    Get a certificate for the app's wallet.
    """
    certificate = await get_certificate(request.app)
    if certificate is None:
        return Response({"detail": "Certificate not found or error fetching."}, status_code=404)

    return Response(certificate, status_code=200)


@post(Endpoint.CERTIFICATES_SELF)
@safe_endpoint
async def generate_certificate_keypair_endpoint(request: Request, data: GenerateCertificateKeypairRequest) -> Response:
    """
    Generate a certificate keypair for the app's wallet.
    """
    certificate_keypair = await generate_certificate_keypair(request.app, algorithm=data.algorithm)
    if certificate_keypair is None:
        return Response({"detail": "Could not generate certificate pair."}, status_code=400)

    return Response(certificate_keypair, status_code=201)
