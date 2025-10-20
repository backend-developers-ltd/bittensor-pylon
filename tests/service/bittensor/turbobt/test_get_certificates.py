import pytest

from pylon.service.bittensor.models import CertificateAlgorithm, Hotkey, NeuronCertificate, PublicKey


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.neurons.get_certificates.return_value = {
        "hotkey1": {
            "algorithm": 1,
            "public_key": "public_key_1",
        },
        "hotkey2": {
            "algorithm": 1,
            "public_key": "public_key_2",
        },
    }
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_certificates(turbobt_client, subnet_spec):
    result = await turbobt_client._get_certificates(netuid=1)
    assert result == {
        Hotkey("hotkey1"): NeuronCertificate(
            algorithm=CertificateAlgorithm.ED25519,
            public_key=PublicKey("public_key_1"),
        ),
        Hotkey("hotkey2"): NeuronCertificate(
            algorithm=CertificateAlgorithm.ED25519,
            public_key=PublicKey("public_key_2"),
        ),
    }


@pytest.mark.asyncio
async def test_turbobt_client_get_certificates_empty(turbobt_client, subnet_spec):
    subnet_spec.neurons.get_certificates.return_value = None
    result = await turbobt_client._get_certificates(netuid=1)
    assert result == {}
