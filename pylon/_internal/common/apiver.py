from enum import StrEnum


class ApiVersion(StrEnum):
    V1 = "v1"

    @property
    def prefix(self) -> str:
        return f"/api/{self}"
