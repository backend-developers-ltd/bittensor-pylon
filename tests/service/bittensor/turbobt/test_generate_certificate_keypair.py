import pytest

from pylon._internal.common.models import (
    CertificateAlgorithm,
    NeuronCertificateKeypair,
    PrivateKey,
    PublicKey,
)


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.neurons.generate_certificate_keypair.return_value = {
        "algorithm": 1,
        "public_key": "public_key_1",
        "private_key": "private_key_1",
    }
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_generate_certificate_keypair(turbobt_client, subnet_spec):
    result = await turbobt_client.generate_certificate_keypair(
        netuid=1,
        algorithm=CertificateAlgorithm.ED25519,
    )

    assert result == NeuronCertificateKeypair(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("public_key_1"),
        private_key=PrivateKey("private_key_1"),
    )

    subnet_spec.neurons.generate_certificate_keypair.assert_called_once()


@pytest.mark.asyncio
async def test_turbobt_client_generate_certificate_keypair_returns_none_when_no_keypair(turbobt_client, subnet_spec):
    subnet_spec.neurons.generate_certificate_keypair.return_value = None

    result = await turbobt_client.generate_certificate_keypair(
        netuid=1,
        algorithm=CertificateAlgorithm.ED25519,
    )

    assert result is None
    subnet_spec.neurons.generate_certificate_keypair.assert_called_once()
