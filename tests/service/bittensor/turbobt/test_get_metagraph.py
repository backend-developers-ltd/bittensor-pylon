import ipaddress
from unittest.mock import Mock

import pytest
from turbobt.neuron import AxonInfo as TurboBtAxonInfo
from turbobt.neuron import AxonProtocolEnum as TurboBtAxonProtocolEnum
from turbobt.neuron import Neuron as TurboBtNeuron

from pylon.service.bittensor.models import (
    AxonInfo,
    AxonProtocol,
    Block,
    BlockHash,
    Coldkey,
    Hotkey,
    Metagraph,
    Neuron,
)


@pytest.fixture
def subnet_spec(subnet_spec):
    subnet_spec.list_neurons.return_value = [
        TurboBtNeuron(
            subnet=subnet_spec,
            uid=1,
            coldkey="coldkey1",
            hotkey="hotkey1",
            active=True,
            axon_info=TurboBtAxonInfo(
                ip=ipaddress.IPv4Address("192.168.1.1"),
                port=8080,
                protocol=TurboBtAxonProtocolEnum.TCP,
            ),
            prometheus_info=Mock(),
            stake=100.0,
            rank=0.5,
            emission=10.0,
            incentive=0.8,
            consensus=0.9,
            trust=0.7,
            validator_trust=0.6,
            dividends=0.4,
            last_update=1000,
            validator_permit=True,
            pruning_score=50,
        ),
        TurboBtNeuron(
            subnet=subnet_spec,
            uid=2,
            coldkey="coldkey2",
            hotkey="hotkey2",
            active=False,
            axon_info=TurboBtAxonInfo(
                ip=ipaddress.IPv4Address("192.168.1.2"),
                port=8081,
                protocol=TurboBtAxonProtocolEnum.UDP,
            ),
            prometheus_info=Mock(),
            stake=200.0,
            rank=0.6,
            emission=20.0,
            incentive=0.7,
            consensus=0.8,
            trust=0.9,
            validator_trust=0.5,
            dividends=0.3,
            last_update=2000,
            validator_permit=False,
            pruning_score=60,
        ),
    ]
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_metagraph(turbobt_client, subnet_spec):
    """
    Test that get_metagraph returns a Metagraph with neurons indexed by hotkey.
    """
    block = Block(number=1000, hash=BlockHash("0xabc123"))

    result = await turbobt_client.get_metagraph(netuid=1, block=block)

    assert result == Metagraph(
        block=block,
        neurons={
            Hotkey("hotkey1"): Neuron(
                uid=1,
                coldkey=Coldkey("coldkey1"),
                hotkey=Hotkey("hotkey1"),
                active=True,
                axon_info=AxonInfo(ip=ipaddress.IPv4Address("192.168.1.1"), port=8080, protocol=AxonProtocol.TCP),
                stake=100.0,
                rank=0.5,
                emission=10.0,
                incentive=0.8,
                consensus=0.9,
                trust=0.7,
                validator_trust=0.6,
                dividends=0.4,
                last_update=1000,
                validator_permit=True,
                pruning_score=50,
            ),
            Hotkey("hotkey2"): Neuron(
                uid=2,
                coldkey=Coldkey("coldkey2"),
                hotkey=Hotkey("hotkey2"),
                active=False,
                axon_info=AxonInfo(ip=ipaddress.IPv4Address("192.168.1.2"), port=8081, protocol=AxonProtocol.UDP),
                stake=200.0,
                rank=0.6,
                emission=20.0,
                incentive=0.7,
                consensus=0.8,
                trust=0.9,
                validator_trust=0.5,
                dividends=0.3,
                last_update=2000,
                validator_permit=False,
                pruning_score=60,
            ),
        },
    )
