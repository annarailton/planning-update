"""Tests for scraper helpers."""

from collections.abc import Callable

from models import Application, PlanningQuery
from scraper import (
    fetch_latest_applications_cached,
    filter_applications_by_keywords,
    load_cached_applications,
    save_cached_applications,
)


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


def test_cached_applications_round_trip(
    application_factory: Callable[..., Application], tmp_path
) -> None:
    """Cached application payloads should load back into Application models."""
    query = PlanningQuery(ward_name="churchill", status_mode="validated")
    applications = [application_factory()]

    save_cached_applications(query, applications, cache_dir=tmp_path)

    assert load_cached_applications(query, cache_dir=tmp_path) == applications


def test_fetch_latest_applications_cached_reuses_saved_results(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Cached query results should avoid a second live fetch."""
    query = PlanningQuery(ward_name="churchill", status_mode="validated")
    applications = [application_factory()]
    fetch_calls = 0

    def fake_fetch_latest_applications(_: PlanningQuery) -> list[Application]:
        nonlocal fetch_calls
        fetch_calls += 1
        return applications

    monkeypatch.setattr(
        "scraper.fetch_latest_applications", fake_fetch_latest_applications
    )

    first = fetch_latest_applications_cached(query, cache_dir=tmp_path)
    second = fetch_latest_applications_cached(query, cache_dir=tmp_path)

    assert first == applications
    assert second == applications
    assert fetch_calls == 1
