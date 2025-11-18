import os
from functools import cached_property

from bittensor_wallet import Wallet
from pydantic_settings import BaseSettings, SettingsConfigDict

from pylon._internal.common.settings import ENV_FILE, settings
from pylon._internal.common.types import HotkeyName, IdentityName, NetUid, PylonAuthToken, WalletName

IDENTITIES_ENV_FILE = os.environ.get("PYLON_ID_ENV_FILE", ENV_FILE)


class Identity(BaseSettings):
    identity_name: IdentityName
    wallet_name: WalletName
    hotkey_name: HotkeyName
    netuid: NetUid
    token: PylonAuthToken

    model_config = SettingsConfigDict(env_file=IDENTITIES_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    @cached_property
    def wallet(self) -> Wallet:
        return Wallet(
            name=self.wallet_name,
            path=settings.bittensor_wallet_path,
            hotkey=self.hotkey_name,
        )


def get_identities(*names: IdentityName) -> dict[IdentityName, Identity]:
    return {
        name: Identity(_env_prefix=f"PYLON_ID_{name.upper()}_", identity_name=name)  # type: ignore
        for name in names
    }


identities = get_identities(*settings.identities)
