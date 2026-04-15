"""Tests for scraper helpers."""

from collections.abc import Callable

import requests

from planning_update.models import Application, ApplicationRef, PlanningQuery
from planning_update.services.scraper import (
    collect_result_applications,
    enrich_application,
    fetch_applications_for_query,
    fetch_latest_applications,
    fetch_latest_applications_cached,
    filter_applications_by_keywords,
    filter_applications_by_major,
    filter_applications_by_major_refs,
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


def test_filter_applications_by_major_refs_keeps_matching_refs(
    application_factory: Callable[..., Application],
) -> None:
    """Major filtering should keep only applications on the major list."""
    applications = [
        application_factory(application_ref={"value": "26/00281/FUL"}),
        application_factory(application_ref={"value": "26/00282/FUL"}),
    ]

    filtered = filter_applications_by_major_refs(
        applications,
        major_refs={"26/00282/FUL"},
    )

    assert [application.application_ref.value for application in filtered] == [
        "26/00282/FUL"
    ]
    assert filtered[0].is_major_application is True


def test_filter_applications_by_major_returns_original_list_when_disabled(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Major filtering should be a no-op when the query does not enable it.

    This includes not hitting the major applications page at all
    """
    applications = [application_factory()]

    def fail_fetch_major_applications_page(session: requests.Session) -> str:
        raise AssertionError("fetch_major_applications_page should not be called")

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_major_applications_page",
        fail_fetch_major_applications_page,
    )

    filtered = filter_applications_by_major(
        requests.Session(),
        applications,
        query=PlanningQuery(),
    )

    assert filtered == applications


def test_fetch_latest_applications_does_not_hit_major_page_when_disabled(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Non-major runs should not request the Oxford major-applications page."""
    monkeypatch.setattr(
        "planning_update.services.scraper.collect_result_applications",
        lambda session, *, query: ([application_factory()], "07 Apr 2026"),
    )

    def fail_fetch_major_applications_page(session: requests.Session) -> str:
        raise AssertionError("fetch_major_applications_page should not be called")

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_major_applications_page",
        fail_fetch_major_applications_page,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.enrich_application",
        lambda session, application, *, query: application,
    )

    applications, week = fetch_latest_applications(PlanningQuery())

    assert len(applications) == 1
    assert week == "07 Apr 2026"


def test_fetch_latest_applications_cached_reuses_saved_results(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Cached query results should avoid a second live fetch."""
    query = PlanningQuery(ward_name="churchill", status_mode="validated")
    applications = [application_factory()]
    fetch_calls = 0

    def fake_fetch_latest_applications(
        _: PlanningQuery,
    ) -> tuple[list[Application], str]:
        nonlocal fetch_calls
        fetch_calls += 1
        return applications, "07 Apr 2026"

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_latest_applications",
        fake_fetch_latest_applications,
    )

    first = fetch_latest_applications_cached(query, cache_dir=tmp_path)
    second = fetch_latest_applications_cached(query, cache_dir=tmp_path)

    assert first == applications
    assert second == applications
    assert fetch_calls == 1


def test_fetch_applications_for_query_with_week_resolves_live_week_in_debug_mode(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Debug runs should still resolve and return the actual selected week."""
    query = PlanningQuery(status_mode="validated")
    cached_applications = [application_factory()]

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_form",
        lambda session: ("csrf-123", ["13 Apr 2026", "06 Apr 2026"]),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.load_cached_applications",
        lambda query, *, cache_dir: cached_applications,
    )

    applications, week = fetch_applications_for_query(
        query=query,
        debug=True,
    )

    assert applications == cached_applications
    assert week == "13 Apr 2026"


def test_fetch_latest_applications_enriches_keyword_matches(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Keyword searches should enrich only the applications that match by proposal."""
    seen_refs: list[str] = []

    monkeypatch.setattr(
        "planning_update.services.scraper.collect_result_applications",
        lambda session, *, query: (
            [
                application_factory(
                    application_ref={"value": "26/00281/FUL"},
                    proposal="Install ASHP and rooftop PV",
                ),
                application_factory(
                    application_ref={"value": "26/00282/FUL"},
                    proposal="Rear extension",
                ),
            ],
            "07 Apr 2026",
        ),
    )

    def fake_enrich_application(
        session: requests.Session, application: Application, *, query: PlanningQuery
    ) -> Application:
        seen_refs.append(application.application_ref.value)
        return application

    monkeypatch.setattr(
        "planning_update.services.scraper.enrich_application", fake_enrich_application
    )

    applications, week = fetch_latest_applications(
        PlanningQuery(keywords=["heat pump", "ashp", "pv"])
    )

    assert [application.application_ref.value for application in applications] == [
        "26/00281/FUL"
    ]
    assert applications[0].keyword_matches == ["ashp", "pv"]
    assert seen_refs == ["26/00281/FUL"]
    assert week == "07 Apr 2026"


def test_fetch_latest_applications_enriches_major_matches(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Major searches should enrich only the applications on the major list."""
    seen_refs: list[str] = []

    monkeypatch.setattr(
        "planning_update.services.scraper.collect_result_applications",
        lambda session, *, query: (
            [
                application_factory(
                    application_ref={"value": "26/00281/FUL"},
                    proposal="Install ASHP and rooftop PV",
                ),
                application_factory(
                    application_ref={"value": "26/00282/FUL"},
                    proposal="Rear extension",
                ),
            ],
            "07 Apr 2026",
        ),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_major_applications_page",
        lambda session: "<html></html>",
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_major_application_refs",
        lambda html: [ApplicationRef(value="26/00282/FUL")],
    )

    def fake_enrich_application(
        session: requests.Session, application: Application, *, query: PlanningQuery
    ) -> Application:
        seen_refs.append(application.application_ref.value)
        return application

    monkeypatch.setattr(
        "planning_update.services.scraper.enrich_application", fake_enrich_application
    )

    applications, week = fetch_latest_applications(PlanningQuery(major=True))

    assert [application.application_ref.value for application in applications] == [
        "26/00282/FUL"
    ]
    assert applications[0].is_major_application is True
    assert seen_refs == ["26/00282/FUL"]
    assert week == "07 Apr 2026"


def test_enrich_application_skips_summary_page_for_validated_queries(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Validated queries should not hit the summary page just to extract decision fields."""
    requested_urls: list[str] = []

    def fake_fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
        requested_urls.append(page_url)
        return "<html></html>", page_url

    monkeypatch.setattr("planning_update.services.scraper.fetch_page", fake_fetch_page)
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_further_information",
        lambda html: ("Churchill Ward", None),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_important_dates",
        lambda html: ("Mon 16 Mar 2026", "Mon 06 Apr 2026"),
    )

    enriched = enrich_application(
        requests.Session(),
        application_factory(),
        query=PlanningQuery(status_mode="validated"),
    )

    assert enriched.ward == "Churchill Ward"
    assert enriched.consultation_deadline is not None
    assert enriched.status is None
    assert enriched.decision is None
    assert enriched.decided is None
    assert requested_urls == [
        "https://example.com/app?activeTab=details",
        "https://example.com/app?activeTab=dates",
    ]


def test_enrich_application_skips_dates_page_for_decided_queries(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Decided queries should not hit the dates page just to extract deadlines."""
    requested_urls: list[str] = []

    def fake_fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
        requested_urls.append(page_url)
        return "<html></html>", page_url

    monkeypatch.setattr("planning_update.services.scraper.fetch_page", fake_fetch_page)
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_further_information",
        lambda html: ("Churchill Ward", None),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_summary_fields",
        lambda html: ("Decided", "Thu 09 Apr 2026", "Approved"),
    )

    enriched = enrich_application(
        requests.Session(),
        application_factory(),
        query=PlanningQuery(status_mode="decided"),
    )

    assert enriched.ward == "Churchill Ward"
    assert enriched.status == "Decided"
    assert enriched.decision == "Approved"
    assert enriched.consultation_deadline is None
    assert enriched.determination_deadline is None
    assert requested_urls == [
        "https://example.com/app?activeTab=details",
        "https://example.com/app",
    ]
