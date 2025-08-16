from ipaddress import IPv4Address

from pydantic import BaseModel, field_validator

Hotkey = str


# Request models for API endpoints
class SetHyperparamRequest(BaseModel):
    name: str
    value: float | int | str | bool


class UpdateWeightRequest(BaseModel):
    hotkey: str
    weight_delta: float

    @field_validator("hotkey")
    @classmethod
    def validate_hotkey(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("hotkey must be a non-empty string")
        return v


class SetWeightRequest(BaseModel):
    hotkey: str
    weight: float

    @field_validator("hotkey")
    @classmethod
    def validate_hotkey(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("hotkey must be a non-empty string")
        return v


class SetWeightsRequest(BaseModel):
    weights: dict[str, float]

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v):
        if not v:
            raise ValueError("No weights provided")

        for hotkey, weight in v.items():
            if not hotkey or not isinstance(hotkey, str):
                raise ValueError(f"Invalid hotkey: '{hotkey}' must be a non-empty string")
            if not isinstance(weight, int | float):
                raise ValueError(f"Invalid weight for hotkey '{hotkey}': '{weight}' must be a number")

        return v


class SetCommitmentRequest(BaseModel):
    data_hex: str


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
