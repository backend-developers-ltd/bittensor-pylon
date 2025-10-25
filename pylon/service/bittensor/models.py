from enum import IntEnum
from ipaddress import IPv4Address, IPv6Address
from typing import NewType, TypeAlias

from pydantic import BaseModel

# Type aliases - these are not new types as they are used in pylon client as annotations of a user interface,
# so we don't want to get the type checker errors on providing plain str, float etc.

Hotkey: TypeAlias = str
Weight: TypeAlias = float
WeightsMapping: TypeAlias = dict[Hotkey, Weight]

# New types

Coldkey = NewType("Coldkey", str)
BlockHash = NewType("BlockHash", str)
RevealRound = NewType("RevealRound", int)
PublicKey = NewType("PublicKey", str)
PrivateKey = NewType("PrivateKey", str)


class UnknownIntEnumMixin:
    """
    Allows to use int enum with undefined values.
    """

    @classmethod
    def _missing_(cls, value):
        member = int.__new__(cls, value)
        member._name_ = f"UNKNOWN_{value}"
        member._value_ = value
        return member


# Pydantic models


class BittensorModel(BaseModel):
    pass


class Block(BittensorModel):
    number: int
    hash: BlockHash


class AxonProtocol(UnknownIntEnumMixin, IntEnum):
    TCP = 0
    UDP = 1
    HTTP = 4


class AxonInfo(BittensorModel):
    ip: IPv4Address | IPv6Address
    port: int
    protocol: AxonProtocol


class Neuron(BittensorModel):
    uid: int
    coldkey: Coldkey
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


class Metagraph(BittensorModel):
    block: Block
    neurons: dict[Hotkey, Neuron]


class SubnetHyperparams(BittensorModel):
    max_weights_limit: int | None = None
    commit_reveal_weights_enabled: bool | None = None
    # Add more parameters as needed.


class CertificateAlgorithm(UnknownIntEnumMixin, IntEnum):
    ED25519 = 1


class NeuronCertificate(BittensorModel):
    algorithm: CertificateAlgorithm
    public_key: PublicKey


class NeuronCertificateKeypair(NeuronCertificate):
    private_key: PrivateKey
