"""
Tests for the GET /identity/{identity_name}/subnet/{netuid}/certificates/{hotkey} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import Block, CertificateAlgorithm, NeuronCertificate
from pylon._internal.common.types import BlockHash, BlockNumber, PublicKey
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_get_certificate_identity_success(test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient):
    """
    Test getting a specific certificate successfully.
    """
    hotkey = "hotkey1"
    certificate = NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0x1234567890abcdef"),
    )
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with sn1_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_certificate=[certificate],
    ):
        response = await test_client.get(f"/api/v1/identity/sn1/subnet/1/certificates/{hotkey}")

        assert response.status_code == HTTP_200_OK
        assert response.json() == {
            "algorithm": 1,
            "public_key": "0x1234567890abcdef",
        }


@pytest.mark.asyncio
async def test_get_certificate_identity_not_found(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient
):
    """
    Test getting a certificate that doesn't exist.
    """
    hotkey = "hotkey2"
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with sn2_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_certificate=[None],
    ):
        response = await test_client.get(f"/api/v1/identity/sn2/subnet/2/certificates/{hotkey}")

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == {
            "detail": "Certificate not found or error fetching.",
            "status_code": HTTP_404_NOT_FOUND,
        }
