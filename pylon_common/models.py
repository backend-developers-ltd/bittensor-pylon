from ipaddress import IPv4Address

from pydantic import BaseModel

Hotkey = str


class Epoch(BaseModel):
    start: int
    end: int


class AxonInfo(BaseModel):
    ip: IPv4Address
    port: int
    protocol: int


class Neuron(BaseModel):
    uid: int
    coldkey: str
    hotkey: Hotkey
    active: bool
    axon_info: AxonInfo
    stake: float
    rank: float
    emission: float
    incentive: float
    consensus: float
    trust: float
    validator_trust: float
    dividends: float
    last_update: int
    validator_permit: bool
    pruning_score: int


class Metagraph(BaseModel):
    block: int
    block_hash: str
    neurons: dict[Hotkey, Neuron]

    def get_neuron(self, hotkey: Hotkey) -> Neuron | None:
        return self.neurons.get(hotkey, None)

    def get_neurons(self) -> list[Neuron]:
        return list(self.neurons.values())

    def get_active_neurons(self) -> list[Neuron]:
        return [neuron for neuron in self.neurons.values() if neuron.active]
