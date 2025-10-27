from enum import IntEnum, StrEnum
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel

from pylon._internal.common.currency import Currency, Token
from pylon._internal.common.types import (
    AlphaStake,
    AlphaStakeRao,
    BlockHash,
    BlockNumber,
    Coldkey,
    Consensus,
    Dividends,
    Emission,
    EmissionRao,
    Hotkey,
    Incentive,
    MaxWeightsLimit,
    NetUid,
    NeuronActive,
    NeuronUid,
    Port,
    PrivateKey,
    PruningScore,
    PublicKey,
    Rank,
    Stake,
    SubnetActive,
    TaoStake,
    TaoStakeRao,
    Timestamp,
    TotalStake,
    TotalStakeRao,
    Trust,
    ValidatorPermit,
    ValidatorTrust,
)


class UnknownIntEnum(IntEnum):
    """
    Allows to use int enum with undefined values.
    """

    @classmethod
    def _missing_(cls, value):
        assert isinstance(value, int)
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


class AxonProtocol(UnknownIntEnum):
    TCP = 0
    UDP = 1
    HTTP = 4


class AxonInfo(BittensorModel):
    ip: IPv4Address | IPv6Address
    port: Port
    protocol: AxonProtocol


class Stakes(BittensorModel):
    alpha: AlphaStake
    tao: TaoStake
    total: TotalStake


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


class SubnetNeurons(BittensorModel):
    block: Block
    neurons: dict[Hotkey, Neuron]


class SubnetHyperparams(BittensorModel):
    max_weights_limit: MaxWeightsLimit | None = None
    commit_reveal_weights_enabled: CommitReveal | None = None
    # Add more parameters as needed.


class CertificateAlgorithm(UnknownIntEnum):
    ED25519 = 1


class NeuronCertificate(BittensorModel):
    algorithm: CertificateAlgorithm
    public_key: PublicKey


class NeuronCertificateKeypair(NeuronCertificate):
    private_key: PrivateKey


class SubnetState(BittensorModel):
    netuid: NetUid
    hotkeys: list[Hotkey]
    coldkeys: list[Coldkey]
    active: list[SubnetActive]
    validator_permit: list[ValidatorPermit]
    pruning_score: list[PruningScore]
    last_update: list[Timestamp]
    emission: list[EmissionRao]
    dividends: list[Dividends]
    incentives: list[Incentive]
    consensus: list[Consensus]
    trust: list[Trust]
    rank: list[Rank]
    block_at_registration: list[BlockNumber]
    alpha_stake: list[AlphaStakeRao]
    tao_stake: list[TaoStakeRao]
    total_stake: list[TotalStakeRao]
    emission_history: list[list[EmissionRao]]

    @property
    def hotkeys_stakes(self) -> dict[Hotkey, Stakes]:
        return {
            hotkey: Stakes(
                alpha=AlphaStake(Currency[Token.ALPHA].from_rao(alpha)),
                tao=TaoStake(Currency[Token.TAO].from_rao(tao)),
                total=TotalStake(Currency[Token.ALPHA].from_rao(total)),
            )
            for hotkey, alpha, tao, total in zip(self.hotkeys, self.alpha_stake, self.tao_stake, self.total_stake)
        }
