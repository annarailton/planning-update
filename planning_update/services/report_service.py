"""Service-layer orchestration for bulding planning application reports."""

from ..models import (
    Application,
    ApplicationSection,
    PlanningReport,
    ResolvedCliOptions,
)
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
        merged[application_ref] = Application.model_validate(
            current.model_dump()
            | application.model_dump(exclude_none=True)
            | {
                "keyword_matches": keyword_matches or None,
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

    for query in options.queries:
        if query.uses_major_matching():
            major_requested_by_status[query.status_mode] = True
        section_applications = fetch_applications_for_query(
            query=query,
            debug=options.debug,
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
    return PlanningReport(applications=applications, sections=sections)
