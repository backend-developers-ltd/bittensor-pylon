import re
from enum import StrEnum

from pylon._internal.common.apiver import ApiVersion


class Endpoint(StrEnum):
    CERTIFICATES = "/certificates"
    CERTIFICATES_SELF = "/certificates/self"
    CERTIFICATES_HOTKEY = "/certificates/{hotkey:str}"
    NEURONS = "/neurons/{block_number:int}"
    LATEST_NEURONS = "/neurons/latest"
    SUBNET_WEIGHTS = "/weights"

    def format(self, *args, **kwargs) -> str:
        normalized = re.sub(r":.+?}", "}", self)
        return normalized.format(*args, **kwargs)

    def for_version(self, version: ApiVersion, *args, **kwargs):
        formatted = self.format(*args, **kwargs)
        return f"{version.prefix}{formatted}"
