"""Tests for scraper helpers."""

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import requests

from planning_update.models import Application, ApplicationRef, PlanningQuery
from planning_update.services.cache import (
    load_cached_application_details,
    load_cached_applications,
    load_cached_weekly_results,
    save_cached_application_details,
    save_cached_applications,
    save_cached_weekly_results,
)
from planning_update.services.scraper import (
    collect_result_applications,
    enrich_application,
    fetch_applications_for_query,
    fetch_latest_applications,
    fetch_latest_applications_cached,
    filter_applications_by_keywords,
    filter_applications_by_major,
    filter_applications_by_major_refs,
    filter_applications_by_ward_distance,
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


def test_cached_application_details_round_trip(
    application_factory: Callable[..., Application], tmp_path
) -> None:
    """Cached enrichment fields should round-trip by application reference."""
    application = application_factory(
        ward="Churchill Ward",
        parish=None,
        decided=None,
        consultation_deadline="Mon 16 Mar 2026",
        determination_deadline="Mon 06 Apr 2026",
        status=None,
        decision=None,
    )

    save_cached_application_details(application, cache_dir=tmp_path)

    assert load_cached_application_details(
        application.application_ref.value,
        cache_dir=tmp_path,
    ) == {
        "consultation_deadline": "2026-03-16",
        "determination_deadline": "2026-04-06",
        "ward": "Churchill Ward",
    }


def test_cached_weekly_results_round_trip(
    application_factory: Callable[..., Application], tmp_path
) -> None:
    """Shallow weekly-list result cards should round-trip by search scope."""
    query = PlanningQuery(status_mode="validated")
    applications = [application_factory()]

    save_cached_weekly_results(
        query,
        applications,
        week="07 Apr 2026",
        cache_dir=tmp_path,
    )

    assert (
        load_cached_weekly_results(
            query,
            week="07 Apr 2026",
            cache_dir=tmp_path,
        )
        == applications
    )


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


def test_filter_applications_by_major_reuses_cached_major_page(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Major filtering should reuse a fresh cached major-applications page."""
    applications = [application_factory(application_ref={"value": "26/00282/FUL"})]

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_major_applications_page",
        lambda session: (_ for _ in ()).throw(
            AssertionError("fetch_major_applications_page should not be called")
        ),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_major_application_refs",
        lambda html: [ApplicationRef(value="26/00282/FUL")],
    )
    from planning_update.services.cache import save_cached_major_applications_page

    save_cached_major_applications_page(
        "<html>cached major page</html>", cache_dir=tmp_path
    )

    filtered = filter_applications_by_major(
        requests.Session(),
        applications,
        query=PlanningQuery(major=True),
        cache_dir=tmp_path,
    )

    assert [application.application_ref.value for application in filtered] == [
        "26/00282/FUL"
    ]


def test_filter_applications_by_major_refreshes_stale_major_page(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Major filtering should refresh the major-applications page when the cache is stale."""
    applications = [application_factory(application_ref={"value": "26/00282/FUL"})]
    fetch_calls = 0

    from planning_update.services.cache import (
        build_major_applications_cache_path,
        save_cached_major_applications_page,
    )

    save_cached_major_applications_page(
        "<html>stale major page</html>", cache_dir=tmp_path
    )
    cache_path = build_major_applications_cache_path(cache_dir=tmp_path)
    stale_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    stale_payload["cached_at"] = (datetime.now(UTC) - timedelta(days=31)).isoformat()
    cache_path.write_text(
        json.dumps(stale_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    def fake_fetch_major_applications_page(session: requests.Session) -> str:
        nonlocal fetch_calls
        fetch_calls += 1
        return "<html>fresh major page</html>"

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_major_applications_page",
        fake_fetch_major_applications_page,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_major_application_refs",
        lambda html: [ApplicationRef(value="26/00282/FUL")],
    )

    filtered = filter_applications_by_major(
        requests.Session(),
        applications,
        query=PlanningQuery(major=True),
        cache_dir=tmp_path,
    )

    assert [application.application_ref.value for application in filtered] == [
        "26/00282/FUL"
    ]
    assert fetch_calls == 1


def test_filter_applications_by_ward_distance_keeps_only_matching_postcodes(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Ward-distance filtering should keep only postcodes inside the ward buffer."""
    applications = [
        application_factory(
            address="South Oxford Community Centre Lake Street Oxford OX1 4RP"
        ),
        application_factory(
            application_ref={"value": "26/00282/FUL"},
            address="Banbury Town Hall Bridge Street Banbury OX16 5QB",
        ),
    ]

    monkeypatch.setattr(
        "planning_update.services.scraper.postcode_is_within_ward_distance",
        lambda postcode, ward_name, *, distance_meters: postcode == "OX1 4RP",
    )

    filtered = filter_applications_by_ward_distance(
        applications,
        query=PlanningQuery(
            ward_name="Hinksey Park",
            distance_around_ward_meters=402.336,
            distance_around_ward_label="0.25 miles",
        ),
    )

    assert [application.postcode for application in filtered] == ["OX1 4RP"]
    assert filtered[0].inclusion_reason == "Hinksey Park + 0.25 miles"


def test_filter_applications_by_ward_distance_keeps_only_exact_ward_matches(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Exact ward filtering should work locally from the shared weekly list."""
    applications = [
        application_factory(
            address="South Oxford Community Centre Lake Street Oxford OX1 4RP"
        ),
        application_factory(
            application_ref={"value": "26/00282/FUL"},
            address="Littlemore Community Centre Giles Road Oxford OX4 4NL",
        ),
    ]

    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: type(
            "LookupResult",
            (),
            {
                "ward_name": (
                    "Hinksey Park" if postcode == "OX1 4RP" else "Littlemore"
                ),
                "parish_name": None,
            },
        )(),
    )

    filtered = filter_applications_by_ward_distance(
        applications,
        query=PlanningQuery(ward_name="Hinksey Park"),
    )

    assert [application.postcode for application in filtered] == ["OX1 4RP"]
    assert filtered[0].inclusion_reason is None


def test_filter_applications_by_ward_distance_keeps_only_matching_parish_postcodes(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Distance filtering should also work against parish boundaries."""
    applications = [
        application_factory(
            address="Littlemore Community Centre Giles Road Oxford OX4 4NL"
        ),
        application_factory(
            application_ref={"value": "26/00282/FUL"},
            address="Banbury Town Hall Bridge Street Banbury OX16 5QB",
        ),
    ]

    monkeypatch.setattr(
        "planning_update.services.scraper.postcode_is_within_parish_distance",
        lambda postcode, parish_name, *, distance_meters: postcode == "OX4 4NL",
    )

    filtered = filter_applications_by_ward_distance(
        applications,
        query=PlanningQuery(
            parish_name="Littlemore",
            distance_around_parish_meters=402.336,
            distance_around_parish_label="0.25 miles",
        ),
    )

    assert [application.postcode for application in filtered] == ["OX4 4NL"]
    assert filtered[0].inclusion_reason == "Littlemore + 0.25 miles"


def test_filter_applications_by_ward_distance_keeps_only_matching_division_postcodes(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Distance filtering should also work against division boundaries."""
    applications = [
        application_factory(address="Cowley Road Oxford OX4 2RD"),
        application_factory(
            application_ref={"value": "26/00282/FUL"},
            address="Banbury Town Hall Bridge Street Banbury OX16 5QB",
        ),
    ]

    monkeypatch.setattr(
        "planning_update.services.scraper.postcode_is_within_division_distance",
        lambda postcode, division_name, *, distance_meters: postcode == "OX4 2RD",
    )

    filtered = filter_applications_by_ward_distance(
        applications,
        query=PlanningQuery(
            division_name="Cowley",
            distance_around_division_meters=402.336,
            distance_around_division_label="0.25 miles",
        ),
    )

    assert [application.postcode for application in filtered] == ["OX4 2RD"]
    assert filtered[0].inclusion_reason == "Cowley + 0.25 miles"


def test_fetch_latest_applications_does_not_hit_major_page_when_disabled(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Non-major runs should not request the Oxford major-applications page."""
    monkeypatch.setattr(
        "planning_update.services.scraper.collect_result_applications",
        lambda session, *, query, cache_dir, selected_week: (
            [application_factory()],
            "07 Apr 2026",
        ),
    )

    def fail_fetch_major_applications_page(session: requests.Session) -> str:
        raise AssertionError("fetch_major_applications_page should not be called")

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_major_applications_page",
        fail_fetch_major_applications_page,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.enrich_application",
        lambda session, application, *, query, cache_dir: application,
    )

    applications, week = fetch_latest_applications(PlanningQuery())

    assert len(applications) == 1
    assert week == "07 Apr 2026"


def test_collect_result_applications_reuses_cached_weekly_results(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Repeated weekly-list collection should reuse cached shallow results."""
    fetch_results_calls = 0

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_form",
        lambda session: ("csrf-token", ["07 Apr 2026"]),
    )

    def fake_fetch_results_page(
        session: requests.Session,
        *,
        query: PlanningQuery,
        csrf_token: str,
        week: str,
    ) -> tuple[str, str]:
        nonlocal fetch_results_calls
        fetch_results_calls += 1
        return "<html></html>", "https://example.com/results"

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_results_page",
        fake_fetch_results_page,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_applications",
        lambda html, week, page_url: [application_factory()],
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_pagination_urls",
        lambda html, page_url: [],
    )

    first, first_week = collect_result_applications(
        requests.Session(),
        query=PlanningQuery(status_mode="validated"),
        cache_dir=tmp_path,
    )
    second, second_week = collect_result_applications(
        requests.Session(),
        query=PlanningQuery(status_mode="validated"),
        cache_dir=tmp_path,
    )

    assert first == second == [application_factory()]
    assert first_week == second_week == "07 Apr 2026"
    assert fetch_results_calls == 1


def test_collect_result_applications_fetches_the_whole_weekly_list(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Weekly-list fetches should ignore ward/parish and cache the whole status/week pool."""
    captured_payload: dict[str, str] | None = None

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_form",
        lambda session: ("csrf-token", ["07 Apr 2026"]),
    )

    def fake_fetch_results_page(
        session: requests.Session,
        *,
        query: PlanningQuery,
        csrf_token: str,
        week: str,
    ) -> tuple[str, str]:
        nonlocal captured_payload
        captured_payload = query.build_search_payload(csrf_token=csrf_token, week=week)
        return "<html></html>", "https://example.com/results"

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_results_page",
        fake_fetch_results_page,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_applications",
        lambda html, week, page_url: [application_factory()],
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_pagination_urls",
        lambda html, page_url: [],
    )

    applications, week = collect_result_applications(
        requests.Session(),
        query=PlanningQuery(
            ward_name="Headington",
            distance_around_ward_meters=241.402,
            status_mode="validated",
        ),
        cache_dir=tmp_path,
    )

    assert applications == [application_factory()]
    assert week == "07 Apr 2026"
    assert captured_payload == {
        "_csrf": "csrf-token",
        "searchCriteria.parish": "",
        "searchCriteria.ward": "",
        "week": "07 Apr 2026",
        "dateType": "DC_Validated",
        "searchType": "Application",
    }


def test_fetch_latest_applications_falls_back_to_previous_week_when_decided_filters_empty(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Default decided searches should fall back when query filters remove latest results."""
    collected_weeks: list[str | None] = []

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_form",
        lambda session: ("csrf-token", ["25 May 2026", "18 May 2026"]),
    )

    def fake_collect_result_applications(
        session: requests.Session,
        *,
        query: PlanningQuery,
        cache_dir,
        selected_week: str | None,
    ) -> tuple[list[Application], str]:
        collected_weeks.append(selected_week)
        if selected_week == "25 May 2026":
            return (
                [application_factory(proposal="Tree works", decided="Mon 25 May 2026")],
                "25 May 2026",
            )
        return (
            [
                application_factory(
                    application_ref={"value": "26/00836/CPU"},
                    proposal="Certificate for solar panels",
                    decided="Mon 18 May 2026",
                )
            ],
            "18 May 2026",
        )

    monkeypatch.setattr(
        "planning_update.services.scraper.collect_result_applications",
        fake_collect_result_applications,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.enrich_application",
        lambda session, application, *, query, cache_dir: application,
    )

    applications, week = fetch_latest_applications(
        PlanningQuery(keywords=["solar panels"], status_mode="decided"),
        cache_dir=tmp_path,
        selected_week="25 May 2026",
    )

    assert [application.application_ref.value for application in applications] == [
        "26/00836/CPU"
    ]
    assert week == "18 May 2026"
    assert collected_weeks == ["25 May 2026", "18 May 2026"]


def test_collect_result_applications_refreshes_empty_decided_weekly_cache(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Empty decided weekly-list caches should not mask later live results."""
    fetched_weeks: list[str] = []
    week = "18 May 2026"
    weekly_query = PlanningQuery(requested_week=week, status_mode="decided")

    save_cached_weekly_results(weekly_query, [], week=week, cache_dir=tmp_path)

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_form",
        lambda session: ("csrf-token", ["25 May 2026", "18 May 2026"]),
    )

    def fake_fetch_results_page(
        session: requests.Session,
        *,
        query: PlanningQuery,
        csrf_token: str,
        week: str,
    ) -> tuple[str, str]:
        fetched_weeks.append(week)
        return week, "https://example.com/results"

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_results_page",
        fake_fetch_results_page,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_applications",
        lambda html, week, page_url: [application_factory(decided="Mon 18 May 2026")],
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_pagination_urls",
        lambda html, page_url: [],
    )

    applications, selected_week = collect_result_applications(
        requests.Session(),
        query=PlanningQuery(status_mode="decided"),
        cache_dir=tmp_path,
        selected_week=week,
    )

    assert applications == [application_factory(decided="Mon 18 May 2026")]
    assert selected_week == week
    assert fetched_weeks == [week]


def test_collect_result_applications_keeps_explicit_empty_decided_week(
    monkeypatch, tmp_path
) -> None:
    """Explicit week selections should not fall back to a different decided week."""
    fetched_weeks: list[str] = []

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_form",
        lambda session: ("csrf-token", ["25 May 2026", "18 May 2026"]),
    )

    def fake_fetch_results_page(
        session: requests.Session,
        *,
        query: PlanningQuery,
        csrf_token: str,
        week: str,
    ) -> tuple[str, str]:
        fetched_weeks.append(week)
        return week, "https://example.com/results"

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_results_page",
        fake_fetch_results_page,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_applications",
        lambda html, week, page_url: [],
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_pagination_urls",
        lambda html, page_url: [],
    )

    applications, week = collect_result_applications(
        requests.Session(),
        query=PlanningQuery(requested_week="25 May 2026", status_mode="decided"),
        cache_dir=tmp_path,
        selected_week="25 May 2026",
    )

    assert applications == []
    assert week == "25 May 2026"
    assert fetched_weeks == ["25 May 2026"]


def test_fetch_latest_applications_cached_reuses_saved_results(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Cached query results should avoid a second live fetch."""
    query = PlanningQuery(ward_name="churchill", status_mode="validated")
    applications = [application_factory()]
    fetch_calls = 0

    def fake_fetch_latest_applications(
        _: PlanningQuery, *, cache_dir, selected_week
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


def test_fetch_applications_for_query_with_supplied_week_uses_normal_fetch_in_debug_mode(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Debug runs should only affect output/email behavior, not query fetching."""
    query = PlanningQuery(status_mode="validated")
    fetched_applications = [application_factory()]
    seen_selected_weeks: list[str | None] = []

    def fake_fetch_latest_applications(
        _: PlanningQuery, *, selected_week: str | None
    ) -> tuple[list[Application], str]:
        seen_selected_weeks.append(selected_week)
        return fetched_applications, "13 Apr 2026"

    def fail_fetch_latest_applications_cached(*args, **kwargs):
        raise AssertionError("debug mode should not use the whole-query cache")

    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_latest_applications",
        fake_fetch_latest_applications,
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_latest_applications_cached",
        fail_fetch_latest_applications_cached,
    )

    applications, week = fetch_applications_for_query(
        query=query,
        debug=True,
        actual_week="13 Apr 2026",
    )

    assert applications == fetched_applications
    assert week == "13 Apr 2026"
    assert seen_selected_weeks == ["13 Apr 2026"]


def test_fetch_latest_applications_enriches_keyword_matches(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Keyword searches should enrich only the applications that match by proposal."""
    seen_refs: list[str] = []

    monkeypatch.setattr(
        "planning_update.services.scraper.collect_result_applications",
        lambda session, *, query, cache_dir, selected_week: (
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
        session: requests.Session,
        application: Application,
        *,
        query: PlanningQuery,
        cache_dir,
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
        lambda session, *, query, cache_dir, selected_week: (
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
        session: requests.Session,
        application: Application,
        *,
        query: PlanningQuery,
        cache_dir,
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
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Validated queries should not hit the summary page just to extract decision fields."""
    requested_urls: list[str] = []

    def fake_fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
        requested_urls.append(page_url)
        return "<html></html>", page_url

    monkeypatch.setattr("planning_update.services.scraper.fetch_page", fake_fetch_page)
    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: type(
            "LookupResult",
            (),
            {"ward_name": "Churchill Ward", "parish_name": None},
        )(),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_important_dates",
        lambda html: ("Mon 16 Mar 2026", "Mon 06 Apr 2026"),
    )

    enriched = enrich_application(
        requests.Session(),
        application_factory(
            address="169 Windmill Road Oxford Oxfordshire OX3 7DW",
            ward=None,
            parish=None,
            decided=None,
            consultation_deadline=None,
            determination_deadline=None,
            status=None,
            decision=None,
        ),
        query=PlanningQuery(status_mode="validated"),
        cache_dir=tmp_path,
    )

    assert enriched.ward == "Churchill Ward"
    assert enriched.consultation_deadline is not None
    assert enriched.status is None
    assert enriched.decision is None
    assert enriched.decided is None
    assert requested_urls == ["https://example.com/app?activeTab=dates"]


def test_enrich_application_reuses_cached_details_by_application_ref(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Cached enrichment details should avoid re-fetching detail pages."""
    cached_application = application_factory(
        status="Decided",
        decision="Approved",
        decided="Thu 09 Apr 2026",
        ward="Churchill Ward",
    )
    save_cached_application_details(cached_application, cache_dir=tmp_path)

    def fail_fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
        raise AssertionError("fetch_page should not be called when details are cached")

    monkeypatch.setattr("planning_update.services.scraper.fetch_page", fail_fetch_page)
    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: type(
            "LookupResult",
            (),
            {
                "ward_name": "Fresh Ward",
                "parish_name": None,
                "division_name": "Fresh Division",
            },
        )(),
    )

    enriched = enrich_application(
        requests.Session(),
        application_factory(address="169 Windmill Road Oxford Oxfordshire OX3 7DW"),
        query=PlanningQuery(status_mode="decided"),
        cache_dir=tmp_path,
    )

    assert enriched.status == "Decided"
    assert enriched.decision == "Approved"
    assert enriched.decided is not None
    assert enriched.ward == "Churchill Ward"
    assert enriched.division == "Fresh Division"


def test_enrich_application_refreshes_stale_cached_decision_details(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Stale cached decision details should be refreshed from the live summary page."""
    cached_application = application_factory(
        status="Registered",
        decision=None,
        decided=None,
        ward="Churchill Ward",
        consultation_deadline=None,
        determination_deadline=None,
    )
    save_cached_application_details(cached_application, cache_dir=tmp_path)
    cache_path = tmp_path / "application-details" / "26_00281_FUL.json"
    stale_cached_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    stale_cached_payload["decision_details_cached_at"] = (
        datetime.now(UTC) - timedelta(days=8)
    ).isoformat()
    cache_path.write_text(
        json.dumps(stale_cached_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    requested_urls: list[str] = []

    def fake_fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
        requested_urls.append(page_url)
        return "<html></html>", page_url

    monkeypatch.setattr("planning_update.services.scraper.fetch_page", fake_fetch_page)
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_summary_fields",
        lambda html: ("Decided", "Thu 09 Apr 2026", "Approved"),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: type(
            "LookupResult",
            (),
            {
                "ward_name": "Fresh Ward",
                "parish_name": None,
                "division_name": "Fresh Division",
            },
        )(),
    )

    enriched = enrich_application(
        requests.Session(),
        application_factory(address="169 Windmill Road Oxford Oxfordshire OX3 7DW"),
        query=PlanningQuery(status_mode="decided"),
        cache_dir=tmp_path,
    )

    assert requested_urls == ["https://example.com/app"]
    assert enriched.status == "Decided"
    assert enriched.decision == "Approved"
    assert enriched.ward == "Churchill Ward"
    assert enriched.division == "Fresh Division"


def test_enrich_application_pauses_between_enrichment_requests(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Validated enrichment should not pause when only one request is needed."""
    requested_urls: list[str] = []
    sleep_calls: list[float] = []

    def fake_fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
        requested_urls.append(page_url)
        return "<html></html>", page_url

    monkeypatch.setattr("planning_update.services.scraper.fetch_page", fake_fetch_page)
    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: type(
            "LookupResult",
            (),
            {"ward_name": "Churchill Ward", "parish_name": None},
        )(),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_important_dates",
        lambda html: ("Mon 16 Mar 2026", "Mon 06 Apr 2026"),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.time.sleep", sleep_calls.append
    )

    enrich_application(
        requests.Session(),
        application_factory(
            address="169 Windmill Road Oxford Oxfordshire OX3 7DW",
            ward=None,
            parish=None,
            decided=None,
            consultation_deadline=None,
            determination_deadline=None,
            status=None,
            decision=None,
        ),
        query=PlanningQuery(status_mode="validated"),
        cache_dir=tmp_path,
    )

    assert requested_urls == ["https://example.com/app?activeTab=dates"]
    assert sleep_calls == []


def test_enrich_application_skips_dates_page_for_decided_queries(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Decided queries should not hit the dates page just to extract deadlines."""
    requested_urls: list[str] = []

    def fake_fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
        requested_urls.append(page_url)
        return "<html></html>", page_url

    monkeypatch.setattr("planning_update.services.scraper.fetch_page", fake_fetch_page)
    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: type(
            "LookupResult",
            (),
            {"ward_name": "Churchill Ward", "parish_name": None},
        )(),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_summary_fields",
        lambda html: ("Decided", "Thu 09 Apr 2026", "Approved"),
    )

    enriched = enrich_application(
        requests.Session(),
        application_factory(
            address="169 Windmill Road Oxford Oxfordshire OX3 7DW",
            ward=None,
            parish=None,
            decided=None,
            consultation_deadline=None,
            determination_deadline=None,
            status=None,
            decision=None,
        ),
        query=PlanningQuery(status_mode="decided"),
        cache_dir=tmp_path,
    )

    assert enriched.ward == "Churchill Ward"
    assert enriched.status == "Decided"
    assert enriched.decision == "Approved"
    assert enriched.consultation_deadline is None
    assert enriched.determination_deadline is None
    assert requested_urls == ["https://example.com/app"]


def test_enrich_application_uses_postcode_lookup_for_ward_and_parish(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Enrichment should derive ward and parish locally from the application postcode."""
    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: type(
            "LookupResult",
            (),
            {
                "ward_name": "Blackbird Leys",
                "parish_name": "Blackbird Leys",
            },
        )(),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_important_dates",
        lambda html: ("Mon 16 Mar 2026", "Mon 06 Apr 2026"),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_page",
        lambda session, page_url: ("<html></html>", page_url),
    )

    enriched = enrich_application(
        requests.Session(),
        application_factory(
            address="Blackbird Leys Community Centre, Blackbird Leys Road, Oxford OX4 6HW",
            ward=None,
            parish=None,
            decided=None,
            consultation_deadline=None,
            determination_deadline=None,
            status=None,
            decision=None,
        ),
        query=PlanningQuery(status_mode="validated"),
        cache_dir=tmp_path,
    )

    assert enriched.ward == "Blackbird Leys"
    assert enriched.parish == "Blackbird Leys"


def test_enrich_application_leaves_ward_and_parish_empty_when_postcode_lookup_fails(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Enrichment should tolerate postcodes missing from the local lookup data."""
    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: (_ for _ in ()).throw(ValueError("missing postcode")),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_important_dates",
        lambda html: ("Mon 16 Mar 2026", "Mon 06 Apr 2026"),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_page",
        lambda session, page_url: ("<html></html>", page_url),
    )

    enriched = enrich_application(
        requests.Session(),
        application_factory(
            address="1 Test Street, Oxford OX9 9ZZ",
            ward=None,
            parish=None,
            decided=None,
            consultation_deadline=None,
            determination_deadline=None,
            status=None,
            decision=None,
        ),
        query=PlanningQuery(status_mode="validated"),
        cache_dir=tmp_path,
    )

    assert enriched.ward is None
    assert enriched.parish is None


def test_enrich_application_merges_cached_details_across_query_modes(
    application_factory: Callable[..., Application], monkeypatch, tmp_path
) -> None:
    """Validated and decided enrichment should accumulate in one per-ref cache."""
    application = application_factory(
        ward=None,
        parish=None,
        decided=None,
        consultation_deadline=None,
        determination_deadline=None,
        status=None,
        decision=None,
    )
    save_cached_application_details(
        application_factory(
            application_ref={"value": application.application_ref.value},
            parish=None,
            decided=None,
            consultation_deadline="Mon 16 Mar 2026",
            determination_deadline="Mon 06 Apr 2026",
            ward="Churchill Ward",
            status=None,
            decision=None,
        ),
        cache_dir=tmp_path,
    )

    monkeypatch.setattr(
        "planning_update.services.scraper.lookup_postcode_in_oxford_wards",
        lambda postcode: type(
            "LookupResult",
            (),
            {"ward_name": "Churchill Ward", "parish_name": None},
        )(),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.extract_summary_fields",
        lambda html: ("Decided", "Thu 09 Apr 2026", "Approved"),
    )
    monkeypatch.setattr(
        "planning_update.services.scraper.fetch_page",
        lambda session, page_url: ("<html></html>", page_url),
    )

    enriched = enrich_application(
        requests.Session(),
        application,
        query=PlanningQuery(status_mode="decided"),
        cache_dir=tmp_path,
    )

    cached_details = load_cached_application_details(
        application.application_ref.value,
        cache_dir=tmp_path,
    )

    assert enriched.consultation_deadline is not None
    assert enriched.determination_deadline is not None
    assert enriched.status == "Decided"
    assert enriched.decision == "Approved"
    assert cached_details == {
        "consultation_deadline": "2026-03-16",
        "decided": "2026-04-09",
        "decision": "Approved",
        "determination_deadline": "2026-04-06",
        "status": "Decided",
        "ward": "Churchill Ward",
    }
