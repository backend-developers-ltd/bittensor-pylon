import logging

from litestar import Controller, Response, get, post, put, status_codes
from litestar.di import Provide
from litestar.exceptions import NotFoundException

from pylon._internal.common.endpoints import Endpoint
from pylon._internal.common.models import Hotkey, SubnetNeurons
from pylon._internal.common.requests import (
    GenerateCertificateKeypairRequest,
    SetWeightsRequest,
)
from pylon._internal.common.types import BlockNumber, NetUid
from pylon.service.bittensor.client import AbstractBittensorClient
from pylon.service.dependencies import bt_client_identity_dep, bt_client_open_access_dep, identity_dep
from pylon.service.exceptions import BadGatewayException
from pylon.service.tasks import ApplyWeights

logger = logging.getLogger(__name__)


class OpenAccessController(Controller):
    path = "/subnet/{netuid:int}/"
    dependencies = {"bt_client": Provide(bt_client_open_access_dep)}

    @get(Endpoint.NEURONS)
    async def get_neurons(
        self, bt_client: AbstractBittensorClient, block_number: BlockNumber, netuid: NetUid
    ) -> SubnetNeurons:
        """
        Get a metagraph for a block.

        Raises:
            NotFoundException: If block does not exist in subtensor.
        """
        # TurboBT struggles with fetching old blocks (like block 4671121), it is so because of broken backwards
        # compatibility in bittensor, so we are not going to fix it.
        block = await bt_client.get_block(block_number)
        if block is None:
            raise NotFoundException(detail=f"Block {block_number} not found.")
        return await bt_client.get_neurons(netuid, block=block)

    @get(Endpoint.LATEST_NEURONS)
    async def get_latest_neurons(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> SubnetNeurons:
        block = await bt_client.get_latest_block()
        return await bt_client.get_neurons(netuid, block=block)

    @get(Endpoint.CERTIFICATES)
    async def get_certificates_endpoint(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> Response:
        """
        Get all certificates for the subnet at the latest block.
        """
        block = await bt_client.get_latest_block()
        certificates = await bt_client.get_certificates(netuid, block)

        return Response(certificates, status_code=status_codes.HTTP_200_OK)

    @get(Endpoint.CERTIFICATES_HOTKEY)
    async def get_certificate_endpoint(
        self, hotkey: Hotkey, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> Response:
        """
        Get a specific certificate for a hotkey.

        Raises:
            NotFoundException: If certificate could not be found in the blockchain.
        """
        block = await bt_client.get_latest_block()
        certificate = await bt_client.get_certificate(netuid, block, hotkey=hotkey)
        if certificate is None:
            raise NotFoundException(detail="Certificate not found or error fetching.")

        return Response(certificate, status_code=status_codes.HTTP_200_OK)


class IdentityController(OpenAccessController):
    path = "/subnet/{netuid:int}/identity/{identity_name:str}"
    dependencies = {"identity": Provide(identity_dep), "bt_client": Provide(bt_client_identity_dep)}

    @put(Endpoint.SUBNET_WEIGHTS)
    async def put_weights_endpoint(
        self, data: SetWeightsRequest, bt_client: AbstractBittensorClient, netuid: NetUid
    ) -> Response:
        """
        Set multiple hotkeys' weights for the current epoch in a single transaction.
        """
        await ApplyWeights.schedule(bt_client, data.weights, netuid=netuid)

        return Response(
            {
                "detail": "weights update scheduled",
                "count": len(data.weights),
            },
            status_code=status_codes.HTTP_200_OK,
        )

    @get(Endpoint.CERTIFICATES_SELF)
    async def get_own_certificate_endpoint(self, bt_client: AbstractBittensorClient, netuid: NetUid) -> Response:
        """
        Get a certificate for the identity's wallet.

        Raises:
            NotFoundException: If certificate could not be found in the blockchain.
        """
        block = await bt_client.get_latest_block()
        certificate = await bt_client.get_certificate(netuid, block)
        if certificate is None:
            raise NotFoundException(detail="Certificate not found or error fetching.")

        return Response(certificate, status_code=status_codes.HTTP_200_OK)

    @post(Endpoint.CERTIFICATES_SELF)
    async def generate_certificate_keypair_endpoint(
        self, bt_client: AbstractBittensorClient, data: GenerateCertificateKeypairRequest, netuid: NetUid
    ) -> Response:
        """
        Generate a certificate keypair for the app's wallet.

        Raises:
            BadGatewayException: When certificate keypair could not be generated.
        """
        certificate_keypair = await bt_client.generate_certificate_keypair(netuid, data.algorithm)
        if certificate_keypair is None:
            raise BadGatewayException(detail="Could not generate certificate pair.")

        return Response(certificate_keypair, status_code=status_codes.HTTP_201_CREATED)
