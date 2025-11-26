"""
Tests for the POST /subnet/{netuid}/identity/{identity_name}/certificates/self endpoint.
"""

import pytest
from litestar.status_codes import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_502_BAD_GATEWAY
from litestar.testing import AsyncTestClient

from pylon._internal.common.models import (
    CertificateAlgorithm,
    NeuronCertificateKeypair,
    PrivateKey,
    PublicKey,
)
from tests.mock_bittensor_client import MockBittensorClient


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_success(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient
):
    """
    Test generating a certificate keypair successfully.
    """
    keypair = NeuronCertificateKeypair(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0xpublic123456789"),
        private_key=PrivateKey("0xprivate987654321"),
    )

    async with sn1_mock_bt_client.mock_behavior(
        generate_certificate_keypair=[keypair],
    ):
        response = await test_client.post(
            "/api/v1/subnet/1/identity/sn1/certificates/self",
            json={"algorithm": 1},
        )

        assert response.status_code == HTTP_201_CREATED
        assert response.json() == {
            "algorithm": 1,
            "public_key": "0xpublic123456789",
            "private_key": "0xprivate987654321",
        }


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_default_algorithm(
    test_client: AsyncTestClient, sn2_mock_bt_client: MockBittensorClient
):
    """
    Test generating a certificate keypair with default algorithm.
    """
    keypair = NeuronCertificateKeypair(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("0xpublic_default"),
        private_key=PrivateKey("0xprivate_default"),
    )

    async with sn2_mock_bt_client.mock_behavior(
        generate_certificate_keypair=[keypair],
    ):
        response = await test_client.post(
            "/api/v1/subnet/2/identity/sn2/certificates/self",
            json={},
        )

        assert response.status_code == HTTP_201_CREATED
        response_data = response.json()
        assert response_data["algorithm"] == 1


@pytest.mark.asyncio
async def test_generate_certificate_keypair_identity_failure(
    test_client: AsyncTestClient, sn1_mock_bt_client: MockBittensorClient
):
    """
    Test generating a certificate keypair when generation fails.
    """
    async with sn1_mock_bt_client.mock_behavior(
        generate_certificate_keypair=[None],
    ):
        response = await test_client.post(
            "/api/v1/subnet/1/identity/sn1/certificates/self",
            json={"algorithm": 1},
        )

        assert response.status_code == HTTP_502_BAD_GATEWAY
        assert response.json() == {
            "detail": "Could not generate certificate pair.",
            "status_code": HTTP_502_BAD_GATEWAY,
        }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "algorithm",
    [
        pytest.param(0, id="algorithm_zero"),
        pytest.param(2, id="algorithm_two"),
        pytest.param("invalid", id="invalid_type"),
    ],
)
async def test_generate_certificate_keypair_identity_invalid_algorithm(test_client: AsyncTestClient, algorithm):
    """
    Test generating a certificate keypair with invalid algorithm.
    """
    response = await test_client.post(
        "/api/v1/subnet/1/identity/sn1/certificates/self",
        json={"algorithm": algorithm},
    )

    assert response.status_code == HTTP_400_BAD_REQUEST, response.json()
    assert response.json() == {
        "status_code": HTTP_400_BAD_REQUEST,
        "detail": "Validation failed for POST /api/v1/subnet/1/identity/sn1/certificates/self",
        "extra": [
            {
                "message": "Value error, Currently, only algorithm equals 1 is supported which is EdDSA using Ed25519 curve",
                "key": "algorithm",
            }
        ],
    }
