import logging

from litestar import Response, get, post, put, status_codes

from pylon._internal.common.endpoints import Endpoint
from pylon._internal.common.requests import (
    GenerateCertificateKeypairRequest,
    SetWeightsRequest,
)
from pylon._internal.common.settings import settings
from pylon.service.bittensor.client import AbstractBittensorClient
from pylon.service.bittensor.models import Hotkey, Metagraph
from pylon.service.tasks import ApplyWeights

logger = logging.getLogger(__name__)


@get(Endpoint.METAGRAPH)
async def get_metagraph(bt_client: AbstractBittensorClient, block_number: int | None = None) -> Metagraph:
    # TODO: TurboBT struggles with fetching old blocks, for tb try to ask for block 4671121
    block = await bt_client.get_block(block_number) if block_number is not None else None
    return await bt_client.get_metagraph(settings.bittensor_netuid, block=block)


@put(Endpoint.SUBNET_WEIGHTS)
async def put_weights_endpoint(data: SetWeightsRequest, bt_client: AbstractBittensorClient) -> Response:
    """
    Set multiple hotkeys' weights for the current epoch in a single transaction.
    """
    await ApplyWeights.schedule(bt_client, data.weights)

    return Response(
        {
            "detail": "weights update scheduled",
            "count": len(data.weights),
        },
        status_code=status_codes.HTTP_200_OK,
    )


@get(Endpoint.CERTIFICATES)
async def get_certificates_endpoint(bt_client: AbstractBittensorClient) -> Response:
    """
    Get all certificates for the subnet.
    """
    certificates = await bt_client.get_certificates(settings.bittensor_netuid)

    return Response(certificates, status_code=status_codes.HTTP_200_OK)


@get(Endpoint.CERTIFICATES_HOTKEY)
async def get_certificate_endpoint(hotkey: Hotkey, bt_client: AbstractBittensorClient) -> Response:
    """
    Get a specific certificate for a hotkey.
    """
    certificate = await bt_client.get_certificate(settings.bittensor_netuid, hotkey=hotkey)
    if certificate is None:
        return Response(
            {"detail": "Certificate not found or error fetching."}, status_code=status_codes.HTTP_404_NOT_FOUND
        )

    return Response(certificate, status_code=status_codes.HTTP_200_OK)


@get(Endpoint.CERTIFICATES_SELF)
async def get_own_certificate_endpoint(bt_client: AbstractBittensorClient) -> Response:
    """
    Get a certificate for the app's wallet.
    """
    certificate = await bt_client.get_certificate(settings.bittensor_netuid)
    if certificate is None:
        return Response(
            {"detail": "Certificate not found or error fetching."}, status_code=status_codes.HTTP_404_NOT_FOUND
        )

    return Response(certificate, status_code=status_codes.HTTP_200_OK)


@post(Endpoint.CERTIFICATES_SELF)
async def generate_certificate_keypair_endpoint(
    bt_client: AbstractBittensorClient, data: GenerateCertificateKeypairRequest
) -> Response:
    """
    Generate a certificate keypair for the app's wallet.
    """
    certificate_keypair = await bt_client.generate_certificate_keypair(settings.bittensor_netuid, data.algorithm)
    if certificate_keypair is None:
        return Response(
            {"detail": "Could not generate certificate pair."}, status_code=status_codes.HTTP_502_BAD_GATEWAY
        )

    return Response(certificate_keypair, status_code=status_codes.HTTP_201_CREATED)
