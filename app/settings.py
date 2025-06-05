from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bittensor_netuid: int
    bittensor_network: str
    bittensor_wallet_name: str
    bittensor_wallet_hotkey_name: str
    bittensor_wallet_path: str
    bittensor_pylon_db: str = "sqlite+aiosqlite:///bittensor_pylon.sqlite3"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore
