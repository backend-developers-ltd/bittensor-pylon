import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pylon._internal.common.types import (
    ArchiveBlocksCutoff,
    BittensorNetwork,
    IdentityName,
    Tempo,
)

ENV_FILE = os.environ.get("PYLON_ENV_FILE", ".env")


class Settings(BaseSettings):
    # bittensor
    bittensor_network: BittensorNetwork = BittensorNetwork("finney")
    bittensor_archive_network: BittensorNetwork = BittensorNetwork("archive")
    bittensor_archive_blocks_cutoff: ArchiveBlocksCutoff = ArchiveBlocksCutoff(300)
    bittensor_wallet_path: str

    # Identities and access
    identities: list[IdentityName] = Field(default_factory=list)
    open_access_token: str = ""

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


settings = Settings()  # type: ignore
