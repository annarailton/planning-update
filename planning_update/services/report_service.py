"""Service-layer orchestration for bulding planning application reports."""

from ..models import (
    Application,
    ApplicationSection,
    CommitteeSection,
    PlanningReport,
    ResolvedCliOptions,
)
from .committee import (
    fetch_upcoming_committee_applications,
    fetch_upcoming_review_committee_applications,
)
from .oxford_planning_client import resolve_actual_week
from .scraper import fetch_applications_for_query

SECTION_TITLES = {
    "validated": "Validated applications",
    "decided": "Decided applications",
}
NO_MAJOR_APPLICATIONS_MESSAGES = {
    "validated": "There are NO major applications validated this week",
}


def merge_applications(
    existing: list[Application], new: list[Application]
) -> list[Application]:
    """Merge application lists by reference while preserving first-seen order."""
    merged: dict[str, Application] = {
        application.application_ref.value: application for application in existing
    }
    ordered_refs = [application.application_ref.value for application in existing]

    for application in new:
        application_ref = application.application_ref.value
        if application_ref not in merged:
            merged[application_ref] = application
            ordered_refs.append(application_ref)
            continue

        current = merged[application_ref]
        keyword_matches = list(current.keyword_matches or [])
        for keyword in application.keyword_matches or []:
            if keyword not in keyword_matches:
                keyword_matches.append(keyword)
        inclusion_reasons: list[str] = []
        for inclusion_reason in [
            current.inclusion_reason,
            application.inclusion_reason,
        ]:
            if inclusion_reason is None:
                continue
            for reason in inclusion_reason.split("; "):
                if reason not in inclusion_reasons:
                    inclusion_reasons.append(reason)
        merged[application_ref] = Application.model_validate(
            current.model_dump()
            | application.model_dump(exclude_none=True)
            | {
                "keyword_matches": keyword_matches or None,
                "inclusion_reason": "; ".join(inclusion_reasons) or None,
                "is_major_application": (
                    current.is_major_application or application.is_major_application
                ),
            }
        )

    return [merged[application_ref] for application_ref in ordered_refs]


def build_planning_report(*, options: ResolvedCliOptions) -> PlanningReport:
    """Run resolved queries and build the rendered report sections."""
    applications_by_status: dict[str, list[Application]] = {
        "validated": [],
        "decided": [],
    }
    major_requested_by_status = {
        "validated": False,
        "decided": False,
    }
    actual_week = resolve_actual_week(options.queries[0]) if options.queries else None

    for query in options.queries:
        if query.uses_major_matching():
            major_requested_by_status[query.status_mode] = True
        section_applications, selected_week = fetch_applications_for_query(
            query=query,
            debug=options.debug,
            actual_week=actual_week,
        )
        applications_by_status[query.status_mode] = merge_applications(
            applications_by_status[query.status_mode],
            section_applications,
        )

    sections = [
        ApplicationSection(
            title=SECTION_TITLES[status_mode],
            applications=applications_by_status[status_mode],
            major_apps_notice_message=(
                NO_MAJOR_APPLICATIONS_MESSAGES[status_mode]
                if (
                    status_mode in NO_MAJOR_APPLICATIONS_MESSAGES
                    and major_requested_by_status[status_mode]
                    and not any(
                        application.is_major_application
                        for application in applications_by_status[status_mode]
                    )
                )
                else None
            ),
            empty_state_message=(
                "No applications"
                if options.status_mode == "both" or status_mode == options.status_mode
                else "Not searched"
            ),
        )
        for status_mode in ["validated", "decided"]
    ]
    applications = (
        applications_by_status["validated"] + applications_by_status["decided"]
    )
    committee_applications = fetch_upcoming_committee_applications()
    review_committee_applications = fetch_upcoming_review_committee_applications()
    return PlanningReport(
        applications=applications,
        sections=sections,
        actual_week=actual_week,
        committee_section=CommitteeSection(applications=committee_applications),
        review_committee_section=(
            CommitteeSection(
                title="Coming to next planning REVIEW committee",
                applications=review_committee_applications,
            )
            if review_committee_applications
            else None
        ),
    )
