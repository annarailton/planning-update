"""Service-layer orchestration for planning application reports."""

from models import Application, ApplicationSection, PlanningReport, ResolvedCliOptions
from scraper import fetch_applications_for_query, merge_applications

SECTION_TITLES = {
    "validated": "Validated applications",
    "decided": "Decided applications",
}


def build_planning_report(*, options: ResolvedCliOptions) -> PlanningReport:
    """Run resolved queries and build the rendered report sections."""
    applications_by_status: dict[str, list[Application]] = {
        "validated": [],
        "decided": [],
    }

    for query in options.queries:
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
