from enum import IntEnum
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel

from pylon._internal.common.types import (
    BlockHash,
    BlockNumber,
    Coldkey,
    CommitRevealEnabled,
    Consensus,
    Dividends,
    Emission,
    Hotkey,
    Incentive,
    MaxWeightsLimit,
    NeuronUid,
    Port,
    PrivateKey,
    PruningScore,
    PublicKey,
    Rank,
    Stake,
    Timestamp,
    Trust,
    ValidatorTrust,
)


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
    number: BlockNumber
    hash: BlockHash


class AxonProtocol(UnknownIntEnumMixin, IntEnum):
    TCP = 0
    UDP = 1
    HTTP = 4


class AxonInfo(BittensorModel):
    ip: IPv4Address | IPv6Address
    port: Port
    protocol: AxonProtocol


class Neuron(BittensorModel):
    uid: NeuronUid
    coldkey: Coldkey
    hotkey: Hotkey
    active: bool
    axon_info: AxonInfo
    stake: Stake
    rank: Rank
    emission: Emission
    incentive: Incentive
    consensus: Consensus
    trust: Trust
    validator_trust: ValidatorTrust
    dividends: Dividends
    last_update: Timestamp
    validator_permit: bool
    pruning_score: PruningScore


class Metagraph(BittensorModel):
    block: Block
    neurons: dict[Hotkey, Neuron]


class SubnetHyperparams(BittensorModel):
    max_weights_limit: MaxWeightsLimit | None = None
    commit_reveal_weights_enabled: CommitRevealEnabled | None = None
    # Add more parameters as needed.


class CertificateAlgorithm(UnknownIntEnumMixin, IntEnum):
    ED25519 = 1


class NeuronCertificate(BittensorModel):
    algorithm: CertificateAlgorithm
    public_key: PublicKey


class NeuronCertificateKeypair(NeuronCertificate):
    private_key: PrivateKey
