"""
Tests for the GET /subnet/{netuid}/certificates/{hotkey} endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import Block, CertificateAlgorithm, NeuronCertificate
from pylon._internal.common.types import BlockHash, BlockNumber, PublicKey
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_get_certificate_open_access_success(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient
):
    """
    Test getting a specific certificate successfully.
    """
    hotkey = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
    certificate = NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0x1234567890abcdef"),
    )
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_certificate=[certificate],
    ):
        response = await test_client.get(f"/api/v1/subnet/1/certificates/{hotkey}")

        assert response.status_code == HTTP_200_OK
        assert response.json() == {
            "algorithm": 1,
            "public_key": "0x1234567890abcdef",
        }


@pytest.mark.asyncio
async def test_get_certificate_open_access_not_found(
    test_client: AsyncTestClient, open_access_mock_bt_client: MockBittensorClient
):
    """
    Test getting a certificate that doesn't exist.
    """
    hotkey = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with open_access_mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_certificate=[None],
    ):
        response = await test_client.get(f"/api/v1/subnet/1/certificates/{hotkey}")

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == {
            "detail": "Certificate not found or error fetching.",
        }
