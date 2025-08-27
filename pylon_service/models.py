from typing import Annotated

from pydantic import BaseModel, Field
from pydantic.types import StringConstraints


class SetHyperparamRequest(BaseModel):
    name: str
    value: float | int | str | bool


class UpdateWeightRequest(BaseModel):
    hotkey: Annotated[str, StringConstraints(min_length=1)]
    weight_delta: float


class SetWeightRequest(BaseModel):
    hotkey: Annotated[str, StringConstraints(min_length=1)]
    weight: float


class SetWeightsRequest(BaseModel):
    weights: dict[
        Annotated[str, StringConstraints(min_length=1)],
        float | int,
    ] = Field(min_length=1)


class SetCommitmentRequest(BaseModel):
    data_hex: str


class Epoch(BaseModel):
    start: int
    end: int
