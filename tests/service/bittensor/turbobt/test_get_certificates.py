import pytest

from pylon._internal.common.types import BlockHash, BlockNumber, Hotkey, PublicKey
from pylon._internal.common.models import Block, CertificateAlgorithm, NeuronCertificate


@pytest.fixture
def test_block():
    return Block(number=BlockNumber(1000), hash=BlockHash("0xabc123"))


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
async def test_turbobt_client_get_certificates(turbobt_client, subnet_spec, test_block):
    result = await turbobt_client.get_certificates(netuid=1, block=test_block)
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
async def test_turbobt_client_get_certificates_empty(turbobt_client, subnet_spec, test_block):
    subnet_spec.neurons.get_certificates.return_value = None
    result = await turbobt_client.get_certificates(netuid=1, block=test_block)
    assert result == {}
