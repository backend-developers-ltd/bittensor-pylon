"""
Tests for the GET /identity/{identity_name}/subnet/{netuid}/certificates endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import Block, CertificateAlgorithm, NeuronCertificate
from pylon._internal.common.types import BlockHash, BlockNumber, PublicKey
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "certificates_input,expected_response",
    [
        pytest.param(
            {
                "hotkey1": NeuronCertificate(
                    algorithm=CertificateAlgorithm.ED25519,
                    public_key=PublicKey("0x1234567890abcdef"),
                ),
                "hothey2": NeuronCertificate(
                    algorithm=CertificateAlgorithm.ED25519,
                    public_key=PublicKey("0xfedcba0987654321"),
                ),
            },
            {
                "hotkey1": {
                    "algorithm": 1,
                    "public_key": "0x1234567890abcdef",
                },
                "hothey2": {
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
async def test_get_certificates_identity(
    test_client: AsyncTestClient,
    sn1_mock_bt_client: MockBittensorClient,
    certificates_input: dict,
    expected_response: dict,
):
    """
    Test getting certificates from the subnet.
    """
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))
    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_certificates=[certificates_input],
    ):
        response = await test_client.get("/api/v1/identity/sn1/subnet/1/certificates")

        assert response.status_code == HTTP_200_OK
        assert response.json() == expected_response
