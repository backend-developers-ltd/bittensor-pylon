from pydantic import BaseModel


class Epoch(BaseModel):
    epoch_start: int
    epoch_end: int


class Neuron(BaseModel):
    uid: int
    hotkey: str
    stake: float
    rank: float
    trust: float
    consensus: float
    incentive: float
    dividends: float
    emission: float


class Metagraph(BaseModel):
    block: int
    block_hash: str
    neurons: list[Neuron]
