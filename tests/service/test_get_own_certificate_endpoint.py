"""
Tests for the GET /certificates/self endpoint.
"""

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.testing import AsyncTestClient

from pylon._internal.common.types import BlockHash, BlockNumber, PublicKey
from pylon.service.bittensor.models import Block, CertificateAlgorithm, NeuronCertificate
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_get_own_certificate_success(test_client: AsyncTestClient, mock_bt_client: MockBittensorClient):
    """
    Test getting own certificate successfully.
    """
    certificate = NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0xabcdef1234567890"),
    )
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_certificate=[certificate],
    ):
        response = await test_client.get("/api/v1/certificates/self")

        assert response.status_code == HTTP_200_OK
        assert response.json() == {
            "algorithm": 1,
            "public_key": "0xabcdef1234567890",
        }


@pytest.mark.asyncio
async def test_get_own_certificate_not_found(test_client: AsyncTestClient, mock_bt_client: MockBittensorClient):
    """
    Test getting own certificate when it doesn't exist.
    """
    latest_block = Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))

    async with mock_bt_client.mock_behavior(
        get_latest_block=[latest_block],
        get_certificate=[None],
    ):
        response = await test_client.get("/api/v1/certificates/self")

        assert response.status_code == HTTP_404_NOT_FOUND
        assert response.json() == {
            "detail": "Certificate not found or error fetching.",
        }
