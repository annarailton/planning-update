"""Helpers for loading CLI defaults from a local TOML config file."""

import tomllib
from pathlib import Path
from typing import Any

from .models import (
    CliConfig,
    CliInputs,
    PlanningQuery,
    ResolvedCliOptions,
)


def parse_wards(value: Any) -> list[str]:
    """Parse ward config values into a deduplicated list."""
    if value is None:
        return []

    parts: list[str]
    if isinstance(value, str):
        parts = value.split(",")
    elif isinstance(value, list):
        parts = [str(item) for item in value]
    else:
        raise TypeError("ward must be provided as a comma-delimited string or list")

    normalized_wards: list[str] = []
    seen: set[str] = set()
    for part in parts:
        ward = part.strip()
        normalized_key = ward.lower()
        if not ward or normalized_key in seen:
            continue
        seen.add(normalized_key)
        normalized_wards.append(ward)
    return normalized_wards


def parse_keywords(value: Any) -> list[str]:
    """Parse keyword config values into a normalized lowercase list."""
    if value is None:
        return []

    parts: list[str]
    if isinstance(value, str):
        parts = value.split(",")
    elif isinstance(value, list):
        parts = [str(item) for item in value]
    else:
        raise TypeError("keywords must be provided as a comma-delimited string or list")

    normalized_keywords: list[str] = []
    seen: set[str] = set()
    for part in parts:
        keyword = part.strip().lower()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        normalized_keywords.append(keyword)
    return normalized_keywords


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
    return CliConfig.model_validate(config_values)


def resolve_cli_options(
    *, cli_inputs: CliInputs, cli_config: CliConfig
) -> ResolvedCliOptions:
    """Merge raw CLI inputs with config defaults into runtime options.

    This resolves each CLI field against the config file, normalizes keywords once,
    and expands the resulting query set for the scraper.

    Query expansion works like this:

    | Input mode    | Query scopes                                                           |
    | ------------- | ---------------------------------------------------------------------- |
    | keyword only  | One all-ward/all-parish keyword scope                                  |
    | location only | One scope per configured ward plus one scope for a configured parish   |
    | both          | Location scopes plus one all-ward/all-parish keyword scope             |

    If we have both we do the location-filtered queries first.
    """
    status_mode = cli_inputs.status or cli_config.status_mode or "both"
    ward_names = parse_wards(
        cli_inputs.ward if cli_inputs.ward is not None else cli_config.ward
    )
    parish_name = (
        cli_inputs.parish if cli_inputs.parish is not None else cli_config.parish
    )
    requested_week = cli_inputs.week if cli_inputs.week is not None else cli_config.week
    keywords = parse_keywords(
        cli_inputs.keywords if cli_inputs.keywords is not None else cli_config.keywords
    )
    major = cli_inputs.major if cli_inputs.major is not None else cli_config.major
    distance_around_ward_meters = cli_config.distance_around_ward
    distance_around_parish_meters = cli_config.distance_around_parish
    # These are for the final report card so it's what the user specified in the config, not the normalized distance value.
    distance_around_ward_label = cli_config.distance_around_ward_label
    distance_around_parish_label = cli_config.distance_around_parish_label

    if distance_around_ward_meters > 0 and not ward_names:
        raise ValueError("distance_around_ward requires at least one ward.")
    if distance_around_parish_meters > 0 and parish_name is None:
        raise ValueError("distance_around_parish requires a parish.")

    query_variants: list[dict[str, object]] = []
    for ward_name in ward_names:
        query_variants.append(
            {
                "ward_name": ward_name,
                "requested_week": requested_week,
                "distance_around_ward_meters": distance_around_ward_meters,
                "distance_around_ward_label": distance_around_ward_label,
            }
        )
    if parish_name is not None:
        query_variants.append(
            {
                "parish_name": parish_name,
                "requested_week": requested_week,
                "distance_around_parish_meters": distance_around_parish_meters,
                "distance_around_parish_label": distance_around_parish_label,
            }
        )
    if (
        not ward_names
        and parish_name is None
        and not keywords
        and (not major or status_mode == "decided")
    ):
        # Fall back to the default all-ward/all-parish query when no other
        # weekly-list scope exists.
        query_variants.append(
            {
                "requested_week": requested_week,
            }
        )
    if keywords:
        # Keyword searches always run across all wards/parishes.
        query_variants.append(
            {
                "keywords": keywords,
                "requested_week": requested_week,
            }
        )
    if major:
        # Major-application matching runs against the current major application
        # list so it always searches across all wards/parishes first.
        query_variants.append(
            {
                "major": True,
                "requested_week": requested_week,
            }
        )
    queries: list[PlanningQuery] = []
    if status_mode == "both":
        # Preserve a stable output order: all validated queries first, then decided.
        for query_variant in query_variants:
            queries.append(PlanningQuery(**query_variant, status_mode="validated"))
        for query_variant in query_variants:
            queries.append(PlanningQuery(**query_variant, status_mode="decided"))
    else:
        for query_variant in query_variants:
            queries.append(PlanningQuery(**query_variant, status_mode=status_mode))

    # Slight bodge to filter out any major + decided queries which don't make
    # sense as once decided will be removed from list.
    # This was more readable than adding more logic above.
    queries = [
        query
        for query in queries
        if not (query.major and query.status_mode == "decided")
    ]

    return ResolvedCliOptions(
        debug=cli_inputs.debug or cli_config.debug is True,
        email_recipient=(
            cli_inputs.email_to
            if cli_inputs.email_to is not None
            else cli_config.email_to
        ),
        status_mode=status_mode,
        queries=queries,
    )
