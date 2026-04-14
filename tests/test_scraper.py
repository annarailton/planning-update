"""Tests for scraper helpers."""

from collections.abc import Callable

from models import Application, PlanningQuery
from scraper import filter_applications_by_keywords


def test_filter_applications_by_keywords_keeps_matching_proposals(
    application_factory: Callable[..., Application],
) -> None:
    """Keyword filtering should keep only matching proposals and annotate them."""
    applications = [
        application_factory(proposal="Install ASHP and rooftop PV"),
        application_factory(
            application_ref={"value": "26/00282/FUL"},
            proposal="Rear extension",
        ),
    ]

    filtered = filter_applications_by_keywords(
        applications,
        query=PlanningQuery(keywords=["heat pump", "ashp", "pv"]),
    )

    assert len(filtered) == 1
    assert filtered[0].proposal == "Install ASHP and rooftop PV"
    assert filtered[0].keyword_matches == ["ashp", "pv"]
