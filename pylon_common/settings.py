from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # bittensor
    bittensor_netuid: int
    bittensor_network: str = "finney"
    bittensor_wallet_name: str
    bittensor_wallet_hotkey_name: str
    bittensor_wallet_path: str

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
    commit_cycle_length: int = 3  # Number of tempos to wait between weight commitments
    commit_window_start_offset: int = 180  # Offset from interval start to begin commit window
    commit_window_end_buffer: int = 10  # Buffer at the end of commit window before interval ends

    # task-specific: how often to run
    weight_commit_check_task_interval_seconds: int = 60
    fetch_hyperparams_task_interval_seconds: int = 60
    fetch_latest_metagraph_task_interval_seconds: int = 10

    # metagraph cache
    metagraph_cache_ttl: int = 600  # TODO: not 10 minutes
    metagraph_cache_maxsize: int = 1000

    # sentry
    sentry_dsn: str = ""
    sentry_environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore
