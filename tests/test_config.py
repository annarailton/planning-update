"""Tests for loading CLI defaults from config files."""

from pathlib import Path

from config import load_cli_config


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
                'output = "emails/applications.html"',
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
    assert config.output == (tmp_path / "emails" / "applications.html").resolve()
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
