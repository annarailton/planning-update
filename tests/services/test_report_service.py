"""Tests for report-building orchestration."""

from collections.abc import Callable

import pytest

from planning_update.models import (
    Application,
    CliStatusMode,
    CommitteeApplication,
    PlanningQuery,
    ResolvedCliOptions,
)
from planning_update.services.report_service import (
    build_planning_report,
    merge_applications,
)


@pytest.fixture(autouse=True)
def no_committee_applications(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep report-service tests focused on weekly-list orchestration by default."""
    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_upcoming_committee_applications",
        lambda: [],
    )


def test_build_planning_report_builds_sections_for_both_statuses(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Both-mode reports should merge applications into validated and decided sections."""
    seen_queries: list[tuple[str, bool, str | None]] = []

    monkeypatch.setattr(
        "planning_update.services.report_service.resolve_actual_week",
        lambda query: "07 Apr 2026",
    )

    def fake_fetch_applications_for_query(
        *, query: PlanningQuery, debug: bool, actual_week: str | None
    ) -> tuple[list[Application], str | None]:
        seen_queries.append((query.status_mode, debug, actual_week))
        if query.status_mode == "validated":
            return [
                application_factory(application_ref={"value": "26/00281/FUL"})
            ], "07 Apr 2026"
        return [
            application_factory(application_ref={"value": "26/00282/FUL"})
        ], "07 Apr 2026"

    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_applications_for_query",
        fake_fetch_applications_for_query,
    )

    report = build_planning_report(
        options=ResolvedCliOptions(
            debug=True,
            status_mode="both",
            queries=[
                PlanningQuery(status_mode="validated"),
                PlanningQuery(status_mode="decided"),
            ],
        )
    )

    assert seen_queries == [
        ("validated", True, "07 Apr 2026"),
        ("decided", True, "07 Apr 2026"),
    ]
    assert [section.title for section in report.sections] == [
        "Validated applications",
        "Decided applications",
    ]
    assert [
        application.application_ref.value for application in report.applications
    ] == [
        "26/00281/FUL",
        "26/00282/FUL",
    ]
    assert report.actual_week == "07 Apr 2026"
    assert report.committee_section is not None
    assert report.committee_section.applications == []
    assert (
        report.committee_section.empty_state_message
        == "No upcoming planning committee agenda released."
    )


def test_build_planning_report_keeps_results_when_later_location_query_is_empty(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """A later ward/parish query should not replace applications already found."""
    monkeypatch.setattr(
        "planning_update.services.report_service.resolve_actual_week",
        lambda query: "18 May 2026",
    )

    def fake_fetch_applications_for_query(
        *, query: PlanningQuery, debug: bool, actual_week: str | None
    ) -> tuple[list[Application], str | None]:
        if query.ward_name == "Churchill":
            return [
                application_factory(application_ref={"value": "26/00817/CEU"})
            ], "18 May 2026"
        return [], "18 May 2026"

    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_applications_for_query",
        fake_fetch_applications_for_query,
    )

    report = build_planning_report(
        options=ResolvedCliOptions(
            debug=True,
            status_mode="validated",
            queries=[
                PlanningQuery(ward_name="Churchill", status_mode="validated"),
                PlanningQuery(ward_name="Marston", status_mode="validated"),
                PlanningQuery(parish_name="Old Marston", status_mode="validated"),
            ],
        )
    )

    assert [
        application.application_ref.value for application in report.applications
    ] == ["26/00817/CEU"]


def test_build_planning_report_adds_committee_section_when_agenda_items_exist(
    application_factory: Callable[..., Application], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reports should include upcoming committee applications when found."""
    monkeypatch.setattr(
        "planning_update.services.report_service.resolve_actual_week",
        lambda query: "07 Apr 2026",
    )
    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_applications_for_query",
        lambda *, query, debug, actual_week: ([application_factory()], "07 Apr 2026"),
    )
    committee_application = CommitteeApplication(
        application_ref={"value": "25/03195/FUL"},
        committee_date="26 May 2026",
        proposal="Demolition and replacement building.",
        address="Mansfield College, Mansfield Road, Oxford",
        agenda_url="https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=568&MId=8165&Ver=4",
        report_url="https://mycouncil.oxford.gov.uk/documents/s90588/report.pdf",
        recommendation="Approve",
    )
    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_upcoming_committee_applications",
        lambda: [committee_application],
    )

    report = build_planning_report(
        options=ResolvedCliOptions(
            debug=False,
            status_mode="validated",
            queries=[PlanningQuery(status_mode="validated")],
        )
    )

    assert report.committee_section is not None
    assert report.committee_section.title == "Coming to next planning committee"
    assert report.committee_section.applications == [committee_application]


def test_build_planning_report_marks_unsearched_section(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Single-status reports should mark the other section as not searched."""
    monkeypatch.setattr(
        "planning_update.services.report_service.resolve_actual_week",
        lambda query: "07 Apr 2026",
    )

    def fake_fetch_applications_for_query(
        *, query: PlanningQuery, debug: bool, actual_week: str | None
    ) -> tuple[list[Application], str | None]:
        return [application_factory()], "07 Apr 2026"

    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_applications_for_query",
        fake_fetch_applications_for_query,
    )

    report = build_planning_report(
        options=ResolvedCliOptions(
            debug=False,
            status_mode="validated",
            queries=[PlanningQuery(status_mode="validated")],
        )
    )

    assert report.sections[0].empty_state_message == "No applications"
    assert report.sections[1].empty_state_message == "Not searched"


def test_build_planning_report_flags_when_no_major_validated_applications_exist(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Validated sections should show a notice when a major query finds none."""
    monkeypatch.setattr(
        "planning_update.services.report_service.resolve_actual_week",
        lambda query: "07 Apr 2026",
    )

    def fake_fetch_applications_for_query(
        *, query: PlanningQuery, debug: bool, actual_week: str | None
    ) -> tuple[list[Application], str | None]:
        if query.major:
            return [], "07 Apr 2026"
        return [application_factory()], "07 Apr 2026"

    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_applications_for_query",
        fake_fetch_applications_for_query,
    )

    report = build_planning_report(
        options=ResolvedCliOptions(
            debug=False,
            status_mode="validated",
            queries=[
                PlanningQuery(status_mode="validated"),
                PlanningQuery(status_mode="validated", major=True),
            ],
        )
    )

    assert report.sections[0].major_apps_notice_message == (
        "There are NO major applications validated this week"
    )
    assert report.sections[1].major_apps_notice_message is None


def test_build_planning_report_does_not_flag_missing_major_decided_applications(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Decided sections should not show a no-major notice."""
    monkeypatch.setattr(
        "planning_update.services.report_service.resolve_actual_week",
        lambda query: "07 Apr 2026",
    )

    def fake_fetch_applications_for_query(
        *, query: PlanningQuery, debug: bool, actual_week: str | None
    ) -> tuple[list[Application], str | None]:
        if query.major:
            return [], "07 Apr 2026"
        return [application_factory()], "07 Apr 2026"

    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_applications_for_query",
        fake_fetch_applications_for_query,
    )

    report = build_planning_report(
        options=ResolvedCliOptions(
            debug=False,
            status_mode="decided",
            queries=[
                PlanningQuery(status_mode="decided"),
                PlanningQuery(status_mode="decided", major=True),
            ],
        )
    )

    assert report.sections[0].major_apps_notice_message is None
    assert report.sections[1].major_apps_notice_message is None


def test_build_planning_report_does_not_flag_when_major_application_exists(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Sections should not show the notice when a major application is present."""
    monkeypatch.setattr(
        "planning_update.services.report_service.resolve_actual_week",
        lambda query: "07 Apr 2026",
    )

    def fake_fetch_applications_for_query(
        *, query: PlanningQuery, debug: bool, actual_week: str | None
    ) -> tuple[list[Application], str | None]:
        if query.major:
            return [application_factory(is_major_application=True)], "07 Apr 2026"
        return [application_factory()], "07 Apr 2026"

    monkeypatch.setattr(
        "planning_update.services.report_service.fetch_applications_for_query",
        fake_fetch_applications_for_query,
    )

    report = build_planning_report(
        options=ResolvedCliOptions(
            debug=False,
            status_mode="validated",
            queries=[
                PlanningQuery(status_mode="validated"),
                PlanningQuery(status_mode="validated", major=True),
            ],
        )
    )

    assert report.sections[0].major_apps_notice_message is None


def test_merge_applications_deduplicates_and_merges_keyword_matches(
    application_factory: Callable[..., Application]
) -> None:
    """Merging should preserve first-seen order and combine keyword matches."""
    existing = [application_factory(keyword_matches=["pv"])]
    new = [
        application_factory(
            keyword_matches=["ashp", "pv"],
            consultation_deadline=None,
        )
    ]

    merged = merge_applications(existing, new)

    assert len(merged) == 1
    assert merged[0].application_ref.value == "26/00281/FUL"
    assert merged[0].keyword_matches == ["pv", "ashp"]


def test_merge_applications_preserves_major_flag_from_any_scope(
    application_factory: Callable[..., Application]
) -> None:
    """Merging should keep the major marker if either query matched it."""
    existing = [application_factory(is_major_application=True)]
    new = [application_factory(is_major_application=False)]

    merged = merge_applications(existing, new)

    assert len(merged) == 1
    assert merged[0].is_major_application is True


def test_merge_applications_preserves_specific_inclusion_reasons_from_multiple_wards(
    application_factory: Callable[..., Application]
) -> None:
    """Merging should keep distinct ward-distance reasons from multiple queries."""
    existing = [application_factory(inclusion_reason="Hinksey Park + 0.25 miles")]
    new = [application_factory(inclusion_reason="Donnington + 0.25 miles")]

    merged = merge_applications(existing, new)

    assert len(merged) == 1
    assert merged[0].inclusion_reason == (
        "Hinksey Park + 0.25 miles; Donnington + 0.25 miles"
    )
