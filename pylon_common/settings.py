import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # bittensor
    bittensor_netuid: int
    bittensor_network: str = "finney"
    bittensor_archive_network: str = "archive"
    bittensor_archive_blocks_cutoff: int = 300
    bittensor_wallet_name: str
    bittensor_wallet_hotkey_name: str
    bittensor_wallet_path: str = "~/.bittensor/wallets/"
    host_wallet_dir: str = (pathlib.Path("~").expanduser() / ".bittensor" / "wallets").as_posix()

    # guard against validator specific endpoints
    am_i_a_validator: bool = False

    # docker
    pylon_docker_image_name: str = "bittensor_pylon"

    # db
    pylon_db_uri: str = "sqlite+aiosqlite:////app/db/pylon.db"
    pylon_db_dir: str = "/tmp/pylon"

    # subnet epoch length
    tempo: int = 360

    # commit-reveal cycle
    commit_weights_task_enable: bool = False
    commit_weights_task_interval_seconds: int = 60
    commit_cycle_length: int = 3  # Number of tempos to wait between weight commitments
    commit_window_start_offset: int = 180  # Offset from interval start to begin commit window
    commit_window_end_buffer: int = 10  # Buffer at the end of commit window before interval ends

    # fetch tasks
    fetch_hyperparams_task_interval_seconds: int = 60
    fetch_latest_metagraph_task_interval_seconds: int = 10

    # metagraph cache
    metagraph_cache_ttl: int = 600  # 10 minutes
    metagraph_cache_maxsize: int = 1000

    # sentry
    sentry_dsn: str = ""
    sentry_environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore
