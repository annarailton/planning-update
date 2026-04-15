"""Tests for report-building orchestration."""

from collections.abc import Callable

from planning_update.models import (
    Application,
    CliStatusMode,
    PlanningQuery,
    ResolvedCliOptions,
)
from planning_update.services.report_service import (
    build_planning_report,
    merge_applications,
)


def test_build_planning_report_builds_sections_for_both_statuses(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Both-mode reports should merge applications into validated and decided sections."""
    seen_queries: list[tuple[str, bool]] = []

    def fake_fetch_applications_for_query(
        *, query: PlanningQuery, debug: bool
    ) -> list[Application]:
        seen_queries.append((query.status_mode, debug))
        if query.status_mode == "validated":
            return [application_factory(application_ref={"value": "26/00281/FUL"})]
        return [application_factory(application_ref={"value": "26/00282/FUL"})]

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

    assert seen_queries == [("validated", True), ("decided", True)]
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


def test_build_planning_report_marks_unsearched_section(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """Single-status reports should mark the other section as not searched."""

    def fake_fetch_applications_for_query(
        *, query: PlanningQuery, debug: bool
    ) -> list[Application]:
        return [application_factory()]

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
