"""Tests for the application data models."""

from datetime import date

import pytest

from config import resolve_cli_options
from models import (
    Application,
    ApplicationRef,
    CliConfig,
    CliInputs,
    PlanningQuery,
)


@pytest.mark.parametrize(
    "reference",
    ["26/00281/FUL", "26/00206/LBC", "26/00744/H42"],
)
def test_application_ref_accepts_known_valid_references(reference: str) -> None:
    """ApplicationRef should accept known valid planning references."""
    assert ApplicationRef(value=reference).value == reference


@pytest.mark.parametrize(
    "reference",
    [
        "skip to main content",
        "26-00281-FUL",
        "26/281/FUL",
    ],
)
def test_application_ref_rejects_invalid_references(reference: str) -> None:
    """ApplicationRef should reject malformed planning references."""
    with pytest.raises(ValueError, match="Invalid application reference"):
        ApplicationRef(value=reference)


def test_application_parses_dates_to_datetimes() -> None:
    """Application should parse Oxford planning date strings to dates."""
    application = Application(
        application_ref=ApplicationRef(value="26/00281/FUL"),
        proposal="Test proposal",
        url="https://example.com",
        address="1 Test Street",
        received="Thu 12 Mar 2026",
        validated="Fri 13 Mar 2026",
        decided="Sat 14 Mar 2026",
        status="Registered",
    )

    assert application.received == date(2026, 3, 12)
    assert application.validated == date(2026, 3, 13)
    assert application.decided == date(2026, 3, 14)


def test_application_model_validate_parses_updated_date_strings() -> None:
    """Application.model_validate should parse updated Oxford date strings."""
    application = Application(
        application_ref=ApplicationRef(value="26/00281/FUL"),
        proposal="Test proposal",
        url="https://example.com",
        address="1 Test Street",
        received="Thu 12 Mar 2026",
        validated="Fri 13 Mar 2026",
    )

    updated = Application.model_validate(
        application.model_dump() | {"decided": "Sat 14 Mar 2026"}
    )

    assert updated.decided == date(2026, 3, 14)


def test_planning_query_build_search_payload_uses_resolved_codes() -> None:
    """PlanningQuery should serialize itself to an Oxford search payload."""
    query = PlanningQuery(
        ward_name="churchill",
        parish_name="littlemore",
        status_mode="decided",
    )

    assert query.build_search_payload(
        csrf_token="token-123",
        week="30 Mar 2026",
    ) == {
        "_csrf": "token-123",
        "searchCriteria.parish": "LPC",
        "searchCriteria.ward": "CHURCH",
        "week": "30 Mar 2026",
        "dateType": "DC_Decided",
        "searchType": "Application",
    }


def test_planning_query_selected_week_uses_requested_week_when_present() -> None:
    """PlanningQuery should prefer an explicitly requested week."""
    query = PlanningQuery(requested_week="30 Mar 2026")

    assert query.selected_week(["06 Apr 2026", "30 Mar 2026"]) == "30 Mar 2026"


def test_planning_query_selected_week_uses_latest_available_week() -> None:
    """PlanningQuery should use the latest available week by default."""
    query = PlanningQuery()

    assert query.selected_week(["06 Apr 2026", "30 Mar 2026"]) == "06 Apr 2026"


def test_planning_query_keyword_mode_ignores_ward_and_parish_filters() -> None:
    """Keyword matching should search across all wards and parishes."""
    query = PlanningQuery(
        ward_name="churchill",
        parish_name="littlemore",
        keywords=["pv", "heat pump"],
    )

    assert query.build_search_payload(
        csrf_token="token-123",
        week="30 Mar 2026",
    ) == {
        "_csrf": "token-123",
        "searchCriteria.parish": "",
        "searchCriteria.ward": "",
        "week": "30 Mar 2026",
        "dateType": "DC_Validated",
        "searchType": "Application",
    }


def test_planning_query_matching_keywords_returns_lowercase_matches() -> None:
    """Keyword matching should return normalized lowercase keyword hits."""
    query = PlanningQuery(keywords=["photovoltaics", "heat pump", "ashp", "pv"])

    assert query.matching_keywords(
        "New PV array and ASHP with rooftop photovoltaics"
    ) == ["photovoltaics", "ashp", "pv"]


def test_cli_keyword_inputs_are_parsed_from_comma_delimited_strings() -> None:
    """CLI config/input models should preserve raw keyword values until resolved."""
    cli_inputs = CliInputs(keywords="photovoltaics, heat pump, ASHP, PV")
    cli_config = CliConfig(keywords="photovoltaics, heat pump, ASHP, PV")

    assert cli_inputs.keywords == "photovoltaics, heat pump, ASHP, PV"
    assert cli_config.keywords == "photovoltaics, heat pump, ASHP, PV"


def test_resolve_cli_options_forces_both_statuses_for_keyword_queries() -> None:
    """Keyword searches should aggregate validated and decided results."""
    options = resolve_cli_options(
        cli_inputs=CliInputs(status="decided", keywords="pv, ashp"),
        cli_config=CliConfig(),
    )

    assert options.status_mode == "both"
    assert options.queries[0].keywords == ["pv", "ashp"]
    assert [query.status_mode for query in options.queries] == [
        "validated",
        "decided",
    ]
