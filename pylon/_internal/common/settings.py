import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pylon._internal.common.types import (
    ArchiveBlocksCutoff,
    BittensorNetwork,
    HotkeyName,
    IdentityName,
    NetUid,
    PylonAuthToken,
    Tempo,
    WalletName,
)

ENV_FILE = os.environ.get("PYLON_ENV_FILE", ".env")


class Identity(BaseSettings):
    identity_name: IdentityName
    wallet_name: WalletName
    hotkey_name: HotkeyName
    netuid: NetUid
    token: PylonAuthToken

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")


class Settings(BaseSettings):
    # bittensor
    bittensor_netuid: NetUid
    bittensor_network: BittensorNetwork = BittensorNetwork("finney")
    bittensor_archive_network: BittensorNetwork = BittensorNetwork("archive")
    bittensor_archive_blocks_cutoff: ArchiveBlocksCutoff = ArchiveBlocksCutoff(300)
    bittensor_wallet_name: str
    bittensor_wallet_hotkey_name: str
    bittensor_wallet_path: str

    # Identities and access
    identities: list[IdentityName] = Field(default_factory=list)
    open_access_token: str = ""

    # metrics
    pylon_metrics_token: str = ""

    # docker
    docker_image_name: str = "bittensor_pylon"

    # subnet epoch length
    tempo: Tempo = Tempo(360)

    # commit-reveal cycle
    commit_cycle_length: int = 3  # Number of tempos to wait between weight commitments
    commit_window_start_offset: int = 180  # Offset from interval start to begin commit window
    commit_window_end_buffer: int = 10  # Buffer at the end of commit window before interval ends

    # weights endpoint behaviour
    weights_retry_attempts: int = 200
    weights_retry_delay_seconds: int = 1

    # sentry
    sentry_dsn: str = ""
    sentry_environment: str = "development"

    # debug
    debug: bool = False

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", env_prefix="PYLON_", extra="ignore")


def get_identities(*names: IdentityName) -> dict[IdentityName, Identity]:
    return {
        name: Identity(_env_prefix=f"PYLON_ID_{name.upper()}_", identity_name=name)  # type: ignore
        for name in names
    }


settings = Settings()  # type: ignore
identities = get_identities(*settings.identities)
