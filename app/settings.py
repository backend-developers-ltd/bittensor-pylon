from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # bittensor
    bittensor_netuid: int
    bittensor_network: str
    bittensor_wallet_name: str
    bittensor_wallet_hotkey_name: str
    bittensor_wallet_path: str

    # db settings
    bittensor_pylon_db: str = "sqlite+aiosqlite:///bittensor_pylon.sqlite3"

    # subnet epoch length
    tempo: int = 360

    # commit-reveal interval settings
    commit_reveal_cycle_length: int = 3  # Number of tempos to wait between weight commitments
    commit_window_start_offset: int = 180  # Offset from interval start to begin commit window
    commit_window_end_buffer: int = 10  # Buffer at the end of commit window before interval ends

    # task-specific settings: how often to run
    weight_commit_check_task_interval_seconds: int = 60
    fetch_hyperparams_task_interval_seconds: int = 60
    fetch_latest_metagraph_task_interval_seconds: int = 10

    # metagraph cache settings
    metagraph_cache_ttl: int = 600  # TODO: not 10 minutes
    metagraph_cache_maxsize: int = 1000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore
