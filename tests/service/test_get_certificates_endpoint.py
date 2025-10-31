"""
Tests for the GET /certificates endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from pylon.service.bittensor.models import Block, BlockHash, CertificateAlgorithm, NeuronCertificate, PublicKey
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "certificates_input,expected_response",
    [
        pytest.param(
            {
                "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty": NeuronCertificate(
                    algorithm=CertificateAlgorithm.ED25519,
                    public_key=PublicKey("0x1234567890abcdef"),
                ),
                "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": NeuronCertificate(
                    algorithm=CertificateAlgorithm.ED25519,
                    public_key=PublicKey("0xfedcba0987654321"),
                ),
            },
            {
                "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty": {
                    "algorithm": 1,
                    "public_key": "0x1234567890abcdef",
                },
                "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": {
                    "algorithm": 1,
                    "public_key": "0xfedcba0987654321",
                },
            },
            id="multiple_certificates",
        ),
        pytest.param(
            {},
            {},
            id="empty_certificates",
        ),
    ],
)
async def test_get_certificates(
    test_client: AsyncTestClient, mock_bt_client: MockBittensorClient, certificates_input: dict, expected_response: dict
):
    """
    Test getting certificates from the subnet.
    """
    latest_block = Block(number=1000, hash=BlockHash("0xabc123"))
    async with mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_certificates=[certificates_input],
    ):
        response = await test_client.get("/api/v1/certificates")

        assert response.status_code == HTTP_200_OK
        assert response.json() == expected_response
