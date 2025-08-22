from pydantic import BaseModel, field_validator


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
