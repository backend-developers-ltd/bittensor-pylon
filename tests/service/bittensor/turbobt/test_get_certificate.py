import pytest

from pylon._internal.common.types import BlockHash, BlockNumber, Hotkey, PublicKey
from pylon._internal.common.models import Block, CertificateAlgorithm, NeuronCertificate


@pytest.fixture
def test_block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


@pytest.fixture
def neuron_spec(neuron_spec):
    neuron_spec.get_certificate.return_value = {
        "algorithm": 1,
        "public_key": "public_key_1",
    }
    return neuron_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_certificate(turbobt_client, neuron_spec, test_block):
    result = await turbobt_client.get_certificate(netuid=1, block=test_block, hotkey=Hotkey("hotkey1"))
    assert result == NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("public_key_1"),
    )


@pytest.mark.asyncio
async def test_turbobt_client_get_certificate_empty(turbobt_client, neuron_spec, test_block):
    neuron_spec.get_certificate.return_value = None
    result = await turbobt_client.get_certificate(netuid=1, block=test_block, hotkey=Hotkey("hotkey1"))
    assert result is None
