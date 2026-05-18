"""Tests for loading CLI defaults from config files."""

from pathlib import Path

import pytest

from planning_update.config import (
    load_cli_config,
    parse_keywords,
    parse_wards,
    resolve_cli_options,
)
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
                'distance_around_ward = "0.25 miles"',
                'distance_around_parish = "0.4 km"',
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
    assert config.distance_around_ward == pytest.approx(402.336, abs=0.001)
    assert config.distance_around_parish == pytest.approx(400.0, abs=0.001)
    assert config.distance_around_ward_label == "0.25 miles"
    assert config.distance_around_parish_label == "0.4 km"
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


def test_load_cli_config_reads_ward_lists(tmp_path: Path) -> None:
    """Config loader should accept TOML ward lists."""
    config_path = tmp_path / "planning_update.toml"
    config_path.write_text(
        'ward = ["churchill", "hinksey park"]',
        encoding="utf-8",
    )

    config = load_cli_config(path=config_path)

    assert config.ward == ["churchill", "hinksey park"]


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


@pytest.mark.parametrize(
    ("raw_value", "expected_meters"),
    [
        ("0.25 miles", pytest.approx(402.336, abs=0.001)),
        ("0.4 km", pytest.approx(400.0, abs=0.001)),
        ("250 meters", pytest.approx(250.0, abs=0.001)),
        ("250 metre", pytest.approx(250.0, abs=0.001)),
        ("1 mile", pytest.approx(1609.344, abs=0.001)),
        ("1 mi", pytest.approx(1609.344, abs=0.001)),
        ("1 kilometre", pytest.approx(1000.0, abs=0.001)),
        ("1 kilometer", pytest.approx(1000.0, abs=0.001)),
        (" 0.25   miles ", pytest.approx(402.336, abs=0.001)),
        ("0", 0.0),
        (0, 0.0),
    ],
)
def test_parse_distance_around_ward_converts_to_meters(
    raw_value: str | int,
    expected_meters: float,
) -> None:
    """Distance-around-ward config values should normalize to meters."""
    assert CliConfig.parse_distance_around_X(raw_value) == expected_meters


@pytest.mark.parametrize(
    ("raw_value", "expected_error", "expected_match"),
    [
        (1, TypeError, "must include units"),
        ("5 seconds", ValueError, "must include length units"),
        ("0.25", ValueError, "must include length units"),
    ],
)
def test_parse_distance_around_ward_rejects_invalid_unit_inputs(
    raw_value: int | str,
    expected_error: type[Exception],
    expected_match: str,
) -> None:
    """Distance-around-ward values should fail clearly for invalid unit inputs."""
    with pytest.raises(expected_error, match=expected_match):
        CliConfig.parse_distance_around_X(raw_value)


@pytest.mark.parametrize(
    "raw_value",
    [
        "five miles",
        "abc",
        "miles",
    ],
)
def test_parse_distance_around_ward_rejects_invalid_distance_strings(
    raw_value: str,
) -> None:
    """Malformed distance strings should fail clearly."""
    with pytest.raises(ValueError, match="must be a valid distance"):
        CliConfig.parse_distance_around_X(raw_value)


def test_parse_wards_accepts_strings_and_lists() -> None:
    """Ward parsing should trim and deduplicate string or list input."""
    assert parse_wards(" Churchill , Hinksey Park, churchill ") == [
        "Churchill",
        "Hinksey Park",
    ]
    assert parse_wards(["Churchill", " Hinksey Park ", "churchill"]) == [
        "Churchill",
        "Hinksey Park",
    ]


def test_parse_keywords_rejects_invalid_types() -> None:
    """Keyword parsing should reject unsupported input types."""
    with pytest.raises(TypeError, match="keywords must be provided"):
        parse_keywords(123)


def test_parse_wards_rejects_invalid_types() -> None:
    """Ward parsing should reject unsupported input types."""
    with pytest.raises(TypeError, match="ward must be provided"):
        parse_wards(123)


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


def test_resolve_cli_options_applies_distance_around_ward_to_location_queries() -> None:
    """Ward-distance config should be carried into location-filtered queries."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(status="validated", ward="Hinksey Park"),
        cli_config=CliConfig(distance_around_ward="0.25 miles"),
    )

    assert len(options.queries) == 1
    assert options.queries[0].ward_name == "Hinksey Park"
    assert options.queries[0].status_mode == "validated"
    assert options.queries[0].distance_around_ward_meters == pytest.approx(
        402.336, abs=0.001
    )
    assert options.queries[0].distance_around_ward_label == "0.25 miles"
    assert options.queries[0].distance_around_parish_meters == 0


def test_resolve_cli_options_rejects_distance_without_ward() -> None:
    """Ward distance config should require at least one ward filter."""
    with pytest.raises(
        ValueError, match="distance_around_ward requires at least one ward"
    ):
        resolve_cli_options(
            cli_inputs=CliInputs(status="validated"),
            cli_config=CliConfig(distance_around_ward="0.25 miles"),
        )


def test_resolve_cli_options_applies_distance_around_ward_to_parish_queries() -> None:
    """Parish distance config should work for parish-filtered queries."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(status="validated"),
        cli_config=CliConfig(
            parish="Littlemore",
            distance_around_parish="0.25 miles",
        ),
    )

    assert len(options.queries) == 1
    assert options.queries[0].parish_name == "Littlemore"
    assert options.queries[0].status_mode == "validated"
    assert options.queries[0].distance_around_parish_meters == pytest.approx(
        402.336, abs=0.001
    )
    assert options.queries[0].distance_around_parish_label == "0.25 miles"
    assert options.queries[0].distance_around_ward_meters == 0


def test_resolve_cli_options_rejects_parish_distance_without_parish() -> None:
    """Parish distance config should require a parish filter."""
    with pytest.raises(ValueError, match="distance_around_parish requires a parish"):
        resolve_cli_options(
            cli_inputs=CliInputs(status="validated"),
            cli_config=CliConfig(distance_around_parish="0.25 miles"),
        )


def test_resolve_cli_options_expands_multiple_wards_from_cli() -> None:
    """Multiple wards should expand into separate location-filtered queries."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(
            ward=["Hinksey Park", "Churchill"],
            status="both",
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
            ward_name="Churchill",
            status_mode="validated",
        ),
        PlanningQuery(
            ward_name="Hinksey Park",
            status_mode="decided",
        ),
        PlanningQuery(
            ward_name="Churchill",
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


def test_resolve_cli_options_expands_multiple_wards_from_config() -> None:
    """Config ward lists should expand into separate location-filtered queries."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(status="validated"),
        cli_config=CliConfig(ward=["Hinksey Park", "Churchill"]),
    )

    assert options.queries == [
        PlanningQuery(
            ward_name="Hinksey Park",
            status_mode="validated",
        ),
        PlanningQuery(
            ward_name="Churchill",
            status_mode="validated",
        ),
    ]


def test_resolve_cli_options_treats_parish_as_additional_location_scope() -> None:
    """A configured parish should add a query instead of narrowing each ward."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(status="validated"),
        cli_config=CliConfig(
            ward=["Churchill", "Marston"],
            parish="Old Marston",
            distance_around_ward="0.15 miles",
        ),
    )

    assert options.queries == [
        PlanningQuery(
            ward_name="Churchill",
            distance_around_ward_meters=241.4016,
            distance_around_ward_label="0.15 miles",
            status_mode="validated",
        ),
        PlanningQuery(
            ward_name="Marston",
            distance_around_ward_meters=241.4016,
            distance_around_ward_label="0.15 miles",
            status_mode="validated",
        ),
        PlanningQuery(
            parish_name="Old Marston",
            status_mode="validated",
        ),
    ]
