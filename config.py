"""Helpers for loading CLI defaults from a local TOML config file."""

import tomllib
from pathlib import Path

from models import (
    CliConfig,
    CliInputs,
    PlanningQuery,
    ResolvedCliOptions,
)


def load_cli_config(path: Path | None = None) -> CliConfig:
    """Load CLI defaults from an explicitly provided TOML file."""
    if path is None:
        return CliConfig()

    config_path = path
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("rb") as config_file:
        raw_config = tomllib.load(config_file)

    config_values = raw_config.get("cli", raw_config)
    config = CliConfig.model_validate(config_values)

    if config.output is not None and not config.output.is_absolute():
        config.output = (config_path.parent / config.output).resolve()

    return config


def resolve_cli_options(
    *, cli_inputs: CliInputs, cli_config: CliConfig
) -> ResolvedCliOptions:
    """Merge raw CLI inputs with config defaults into runtime options."""
    status_mode = cli_inputs.status or cli_config.status_mode or "both"

    fallback_weeks = (
        cli_inputs.fallback_weeks
        if cli_inputs.fallback_weeks is not None
        else cli_config.fallback_weeks if cli_config.fallback_weeks is not None else 1
    )
    strict = (
        cli_inputs.strict
        if cli_inputs.strict is not None
        else cli_config.strict if cli_config.strict is not None else False
    )

    base_query = PlanningQuery(
        ward_name=(cli_inputs.ward if cli_inputs.ward is not None else cli_config.ward),
        parish_name=(
            cli_inputs.parish if cli_inputs.parish is not None else cli_config.parish
        ),
        requested_week=(
            cli_inputs.week if cli_inputs.week is not None else cli_config.week
        ),
        fallback_weeks=max(0, fallback_weeks),
        strict=strict,
        status_mode="validated",
    )

    queries = [base_query.model_copy(update={"status_mode": status_mode})]
    if status_mode == "both":
        queries = [
            base_query.model_copy(update={"status_mode": "validated"}),
            base_query.model_copy(update={"status_mode": "decided"}),
        ]

    return ResolvedCliOptions(
        debug=cli_inputs.debug or cli_config.debug is True,
        output=cli_inputs.output or cli_config.output,
        email_recipient=(
            cli_inputs.email_to
            if cli_inputs.email_to is not None
            else cli_config.email_to
        ),
        status_mode=status_mode,
        queries=queries,
    )
