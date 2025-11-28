import pytest

from pylon._internal.common.models import Block, CertificateAlgorithm, NeuronCertificate
from pylon._internal.common.types import BlockHash, BlockNumber, Hotkey, PublicKey


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
async def test_turbobt_client_get_certificate(turbobt_client, neuron_spec, test_block, subnet_spec):
    result = await turbobt_client.get_certificate(netuid=1, block=test_block, hotkey=Hotkey("hotkey1"))
    assert result == NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("public_key_1"),
    )
    subnet_spec.neuron.assert_called_once_with(hotkey=Hotkey("hotkey1"))


@pytest.mark.asyncio
async def test_turbobt_client_get_certificate_empty(turbobt_client, neuron_spec, test_block):
    neuron_spec.get_certificate.return_value = None
    result = await turbobt_client.get_certificate(netuid=1, block=test_block, hotkey=Hotkey("hotkey1"))
    assert result is None


@pytest.mark.asyncio
async def test_turbobt_client_get_certificate_default(turbobt_client, neuron_spec, test_block, wallet, subnet_spec):
    result = await turbobt_client.get_certificate(netuid=1, block=test_block)
    assert result == NeuronCertificate(
        algorithm=CertificateAlgorithm.ED25519,
        public_key=PublicKey("public_key_1"),
    )
    subnet_spec.neuron.assert_called_once_with(hotkey=wallet.hotkey.ss58_address)


@pytest.mark.asyncio
async def test_turbobt_client_get_certificate_no_hotkey(turbobt_client_no_wallet, neuron_spec, test_block):
    with pytest.raises(ValueError, match=r"No hotkey provided while the client has no wallet\."):
        await turbobt_client_no_wallet.get_certificate(netuid=1, block=test_block)
