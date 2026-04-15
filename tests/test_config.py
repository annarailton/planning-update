"""Tests for loading CLI defaults from config files."""

from pathlib import Path

import pytest

from planning_update.config import load_cli_config, parse_keywords, resolve_cli_options
from planning_update.models import CliConfig, CliInputs, PlanningQuery


def test_load_cli_config_reads_top_level_values(tmp_path: Path) -> None:
    """Config loader should parse top-level TOML values."""
    config_path = tmp_path / "planning_update.toml"
    config_path.write_text(
        "\n".join(
            [
                "debug = true",
                'ward = "churchill"',
                'parish = "Littlemore"',
                'status_mode = "decided"',
                'week = "30 Mar 2026"',
                'keywords = "photovoltaics, heat pump, ASHP, PV"',
                "major = true",
                'email_to = "anna@example.com"',
            ]
        ),
        encoding="utf-8",
    )

    config = load_cli_config(path=config_path)

    assert config.debug is True
    assert config.ward == "churchill"
    assert config.parish == "Littlemore"
    assert config.status_mode == "decided"
    assert config.week == "30 Mar 2026"
    assert config.keywords == "photovoltaics, heat pump, ASHP, PV"
    assert config.major is True
    assert config.email_to == "anna@example.com"


def test_load_cli_config_reads_cli_section(tmp_path: Path) -> None:
    """Config loader should also support a nested cli table."""
    config_path = tmp_path / "planning_update.toml"
    config_path.write_text(
        "\n".join(
            [
                "[cli]",
                'ward = "churchill"',
                'status_mode = "validated"',
            ]
        ),
        encoding="utf-8",
    )

    config = load_cli_config(path=config_path)

    assert config.ward == "churchill"
    assert config.status_mode == "validated"


def test_parse_keywords_normalizes_and_deduplicates_strings() -> None:
    """Keyword parsing should trim, lowercase, and deduplicate values."""
    assert parse_keywords(" photovoltaics , PV, ashp, pv, , ASHP ") == [
        "photovoltaics",
        "pv",
        "ashp",
    ]


def test_parse_keywords_accepts_lists() -> None:
    """Keyword parsing should also accept list inputs."""
    assert parse_keywords(["Heat Pump", " PV ", "heat pump"]) == [
        "heat pump",
        "pv",
    ]


def test_parse_keywords_returns_empty_list_for_none() -> None:
    """Keyword parsing should treat missing values as empty."""
    assert parse_keywords(None) == []


def test_parse_keywords_rejects_invalid_types() -> None:
    """Keyword parsing should reject unsupported input types."""
    with pytest.raises(TypeError, match="keywords must be provided"):
        parse_keywords(123)


def test_resolve_cli_options_defaults_keyword_queries_to_both_statuses() -> None:
    """Keyword searches should use the default both-mode when no status is set."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(keywords="pv, ashp"),
        cli_config=CliConfig(),
    )

    assert options.status_mode == "both"
    assert options.queries == [
        PlanningQuery(keywords=["pv", "ashp"], status_mode="validated"),
        PlanningQuery(keywords=["pv", "ashp"], status_mode="decided"),
    ]


def test_resolve_cli_options_builds_keyword_and_ward_queries_for_both_statuses() -> (
    None
):
    """Keyword-plus-ward searches should query both scopes for both statuses."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(
            ward="Hinksey Park",
            status="both",
            keywords="photovoltaics, heat pump, ASHP, PV, solar panels",
        ),
        cli_config=CliConfig(),
    )

    assert options.status_mode == "both"
    assert options.queries == [
        PlanningQuery(
            ward_name="Hinksey Park",
            status_mode="validated",
        ),
        PlanningQuery(
            keywords=["photovoltaics", "heat pump", "ashp", "pv", "solar panels"],
            status_mode="validated",
        ),
        PlanningQuery(
            ward_name="Hinksey Park",
            status_mode="decided",
        ),
        PlanningQuery(
            keywords=["photovoltaics", "heat pump", "ashp", "pv", "solar panels"],
            status_mode="decided",
        ),
    ]


def test_resolve_cli_options_builds_major_scope_alongside_ward_queries() -> None:
    """Major searches should add only a validated all-wards major query."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(
            ward="Hinksey Park",
            status="both",
        ),
        cli_config=CliConfig(major=True),
    )

    assert options.status_mode == "both"
    assert options.queries == [
        PlanningQuery(
            ward_name="Hinksey Park",
            status_mode="validated",
        ),
        PlanningQuery(
            major=True,
            status_mode="validated",
        ),
        PlanningQuery(
            ward_name="Hinksey Park",
            status_mode="decided",
        ),
    ]


def test_resolve_cli_options_major_only_query() -> None:
    """Major-only runs should only include a validated major query."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(),
        cli_config=CliConfig(major=True),
    )

    assert options.status_mode == "both"
    assert options.queries == [
        PlanningQuery(major=True, status_mode="validated"),
    ]


def test_resolve_cli_options_ignores_major_for_decided_only_runs() -> None:
    """Decided-only runs should not add a major query."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(status="decided"),
        cli_config=CliConfig(major=True),
    )

    assert options.status_mode == "decided"
    assert options.queries == [
        PlanningQuery(status_mode="decided"),
    ]


def test_resolve_cli_options_decided_keywords_keep_keyword_query_but_drop_major() -> (
    None
):
    """Decided keyword runs should keep keywords but strip any decided major query."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(
            status="decided",
            keywords="photovoltaics, heat pump",
        ),
        cli_config=CliConfig(major=True),
    )

    assert options.status_mode == "decided"
    assert options.queries == [
        PlanningQuery(
            keywords=["photovoltaics", "heat pump"],
            status_mode="decided",
        ),
    ]


def test_resolve_cli_options_applies_explicit_status_to_keyword_queries() -> None:
    """An explicit status should apply to keyword and location scopes alike."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(
            ward="Hinksey Park",
            status="decided",
            keywords="photovoltaics, heat pump",
        ),
        cli_config=CliConfig(),
    )

    assert options.status_mode == "decided"
    assert options.queries == [
        PlanningQuery(
            ward_name="Hinksey Park",
            status_mode="decided",
        ),
        PlanningQuery(
            keywords=["photovoltaics", "heat pump"],
            status_mode="decided",
        ),
    ]
