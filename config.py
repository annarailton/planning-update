"""Helpers for loading CLI defaults from a local TOML config file."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, field_validator

from models import ApplicationStatusMode

DEFAULT_CONFIG_FILENAME = "planning_update.toml"


class CliConfig(BaseModel):
    """Optional CLI defaults loaded from TOML."""

    debug: bool | None = None
    ward: str | None = None
    parish: str | None = None
    status_mode: ApplicationStatusMode | None = None
    week: str | None = None
    fallback_weeks: int | None = None
    strict: bool | None = None
    output: Path | None = None
    email_to: str | None = None

    @field_validator("fallback_weeks")
    @classmethod
    def validate_fallback_weeks(cls, value: int | None) -> int | None:
        """Ensure configured fallback weeks are non-negative."""
        if value is None:
            return None
        if value < 0:
            raise ValueError("fallback_weeks must be greater than or equal to 0")
        return value


def default_config_path() -> Path:
    """Return the default config path for the current working directory."""
    return Path(DEFAULT_CONFIG_FILENAME)


def load_cli_config(path: Path | None = None) -> CliConfig:
    """Load CLI defaults from a TOML file when one exists."""
    config_path = path or default_config_path()
    if not config_path.exists():
        if path is not None:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return CliConfig()

    with config_path.open("rb") as config_file:
        raw_config = tomllib.load(config_file)

    config_values = raw_config.get("cli", raw_config)
    config = CliConfig.model_validate(config_values)

    if config.output is not None and not config.output.is_absolute():
        config.output = (config_path.parent / config.output).resolve()

    return config
