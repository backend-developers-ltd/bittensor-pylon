from enum import IntEnum, StrEnum
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel

from pylon._internal.common.types import (
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    Emission,
    Hotkey,
    Incentive,
    MaxWeightsLimit,
    NeuronActive,
    NeuronUid,
    Port,
    PrivateKey,
    PruningScore,
    PublicKey,
    Rank,
    Stake,
    Timestamp,
    Trust,
    ValidatorPermit,
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


class CommitReveal(StrEnum):
    DISABLED = "disabled"
    V2 = "v2"
    V3 = "v3"
    V4 = "v4"


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


class Stakes(BittensorModel):
    alpha: float
    tao: float
    total: float


class Neuron(BittensorModel):
    uid: NeuronUid
    coldkey: Coldkey
    hotkey: Hotkey
    active: NeuronActive
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
    validator_permit: ValidatorPermit
    pruning_score: PruningScore
    # Field below may not be fetched by get_neurons method - it is taken from the subnet's state.
    stakes: Stakes


class Metagraph(BittensorModel):
    block: Block
    neurons: dict[Hotkey, Neuron]


class SubnetHyperparams(BittensorModel):
    max_weights_limit: MaxWeightsLimit | None = None
    commit_reveal_weights_enabled: CommitReveal | None = None
    # Add more parameters as needed.


class CertificateAlgorithm(UnknownIntEnumMixin, IntEnum):
    ED25519 = 1


class NeuronCertificate(BittensorModel):
    algorithm: CertificateAlgorithm
    public_key: PublicKey


class NeuronCertificateKeypair(NeuronCertificate):
    private_key: PrivateKey


class SubnetState(BittensorModel):
    netuid: int
    hotkeys: list[Hotkey]
    coldkeys: list[Coldkey]
    active: list[bool]
    validator_permit: list[bool]
    pruning_score: list[int]
    last_update: list[int]
    emission: list[int]
    dividends: list[int]
    incentives: list[int]
    consensus: list[int]
    trust: list[int]
    rank: list[int]
    block_at_registration: list[int]
    alpha_stake: list[int]
    tao_stake: list[int]
    total_stake: list[int]
    emission_history: list[list[int]]

    @property
    def hotkeys_stakes(self) -> dict[Hotkey, Stakes]:
        return {
            hotkey: Stakes(alpha=alpha / 1_000_000_000, tao=tao / 1_000_000_000, total=total / 1_000_000_000)
            for hotkey, alpha, tao, total in zip(self.hotkeys, self.alpha_stake, self.tao_stake, self.total_stake)
        }
