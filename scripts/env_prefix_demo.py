#!/usr/bin/env python3
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoSettings(BaseSettings):
    """Minimal settings class that mimics the repo-wide env prefix behaviour."""

    foo: str = "foo-default"
    bar_value: str = "bar-default"

    model_config = SettingsConfigDict(env_prefix="PYLON_")


def main() -> None:
    demo = DemoSettings()  # loads PYLON_* env vars if present
    print("Loaded values (note env_prefix affects *inputs* only):")
    print(f"  foo = {demo.foo}")
    print(f"  bar_value = {demo.bar_value}")
    print()
    print("model_dump() output (notice keys have no prefix):")
    for key, value in demo.model_dump().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
