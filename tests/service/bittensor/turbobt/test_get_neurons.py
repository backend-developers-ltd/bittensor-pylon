import ipaddress
from unittest.mock import Mock

import pytest
from turbobt.neuron import AxonInfo as TurboBtAxonInfo
from turbobt.neuron import AxonProtocolEnum as TurboBtAxonProtocolEnum
from turbobt.neuron import Neuron as TurboBtNeuron

from pylon.service.bittensor.models import AxonInfo, AxonProtocol, Coldkey, Hotkey, Neuron, Stakes


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
    subnet_spec.get_state.return_value = {
        "netuid": 1,
        "hotkeys": ["hotkey1", "hotkey2"],
        "coldkeys": ["coldkey1", "coldkey2"],
        "active": [True, False],
        "validator_permit": [True, False],
        "pruning_score": [50, 60],
        "last_update": [1000, 2000],
        "emission": [10_000_000_000, 20_000_000_000],
        "dividends": [400_000_000, 300_000_000],
        "incentives": [800_000_000, 700_000_000],
        "consensus": [900_000_000, 800_000_000],
        "trust": [700_000_000, 900_000_000],
        "rank": [500_000_000, 600_000_000],
        "block_at_registration": [0, 0],
        "alpha_stake": [50_000_000_000, 100_000_000_000],
        "tao_stake": [30_000_000_000, 60_000_000_000],
        "total_stake": [55_400_000_000, 110_800_000_000],
        "emission_history": [[], []],
    }
    return subnet_spec


@pytest.mark.asyncio
async def test_turbobt_client_get_neurons(turbobt_client, subnet_spec):
    result = await turbobt_client._get_neurons(netuid=1)
    assert result == [
        Neuron(
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
            stakes=Stakes(alpha=50.0, tao=30.0, total=55.4),
        ),
        Neuron(
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
            stakes=Stakes(alpha=100.0, tao=60.0, total=110.8),
        ),
    ]
