import pytest

from pylon.service.bittensor.models import CertificateAlgorithm, Hotkey, NeuronCertificate, PublicKey


@pytest.fixture
def neuron_spec(neuron_spec):
    neuron_spec.get_certificate.return_value = {
        "algorithm": 1,
        "public_key": "public_key_1",
    }
    return neuron_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_certificate(turbobt_client, neuron_spec):
    result = await turbobt_client._get_certificate(netuid=1, hotkey=Hotkey("hotkey1"))
    assert result == NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("public_key_1"),
    )


@pytest.mark.asyncio
async def test_turbobt_client_get_certificate_empty(turbobt_client, neuron_spec):
    neuron_spec.get_certificate.return_value = None
    result = await turbobt_client._get_certificate(netuid=1, hotkey=Hotkey("hotkey1"))
    assert result is None
