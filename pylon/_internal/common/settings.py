from pydantic_settings import BaseSettings, SettingsConfigDict

from pylon._internal.common.types import ArchiveBlocksCutoff, BittensorNetwork, NetUid, Tempo


class Settings(BaseSettings):
    # bittensor
    bittensor_netuid: NetUid
    bittensor_network: BittensorNetwork = BittensorNetwork("finney")
    bittensor_archive_network: BittensorNetwork = BittensorNetwork("archive")
    bittensor_archive_blocks_cutoff: ArchiveBlocksCutoff = ArchiveBlocksCutoff(300)
    bittensor_wallet_name: str
    bittensor_wallet_hotkey_name: str
    bittensor_wallet_path: str

    # auth
    auth_token: str = ""

    # docker
    pylon_docker_image_name: str = "bittensor_pylon"

    # db
    pylon_db_uri: str = "sqlite+aiosqlite:////app/db/pylon.db"
    pylon_db_dir: str = "/tmp/pylon"

    # subnet epoch length
    tempo: Tempo = Tempo(360)

    # commit-reveal cycle
    commit_cycle_length: int = 3  # Number of tempos to wait between weight commitments
    commit_window_start_offset: int = 180  # Offset from interval start to begin commit window
    commit_window_end_buffer: int = 10  # Buffer at the end of commit window before interval ends

    # weights endpoint behaviour
    weights_retry_attempts: int = 200
    weights_retry_delay_seconds: int = 1

    # metagraph cache
    metagraph_cache_ttl: int = 600  # TODO: not 10 minutes
    metagraph_cache_maxsize: int = 1000

    # sentry
    sentry_dsn: str = ""
    sentry_environment: str = "development"

    # debug
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore
