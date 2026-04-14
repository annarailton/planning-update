"""Tests for loading CLI defaults from config files."""

from pathlib import Path

import pytest

from config import load_cli_config, parse_keywords


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
