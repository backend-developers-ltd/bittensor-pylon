import typing
from abc import ABC
from ipaddress import IPv4Address

from pydantic import BaseModel, field_validator

from pylon._internal.common.apiver import ApiVersion
from pylon._internal.common.endpoints import Endpoint

Hotkey = str

CertificateAlgorithm: typing.TypeAlias = int
PrivateKey: typing.TypeAlias = str
PublicKey: typing.TypeAlias = str


class PylonRequest(BaseModel, ABC):
    http_method: typing.ClassVar[str]
    endpoint: typing.ClassVar[Endpoint]
    api_version: typing.ClassVar[ApiVersion]

    def request_args(self) -> dict:
        """
        Returns args to be passed to the httpx client 'request' method to make a proper request.
        """
        return {
            "method": self.http_method,
            "url": self.endpoint.for_version(self.api_version),
            "json": self.model_dump(),
        }


class SetWeightsRequest(PylonRequest):
    http_method = "PUT"
    endpoint = Endpoint.SUBNET_WEIGHTS
    api_version = ApiVersion.V1

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


class GenerateCertificateKeypairRequest(BaseModel):
    algorithm: CertificateAlgorithm = 1  # EdDSA using ed25519 curve

    @classmethod
    @field_validator("algorithm")
    def validate_algorithm(cls, v):
        if not isinstance(v, int) and v != 1:
            raise ValueError("Currently, only algorithm equals 1 is supported which is EdDSA using Ed25519 curve")
        return v


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


class Certificate(BaseModel):
    algorithm: CertificateAlgorithm = 1  # EdDSA using ed25519 curve
    public_key: PublicKey


class CertificateKeypair(Certificate):
    private_key: PrivateKey
