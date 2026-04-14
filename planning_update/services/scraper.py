"""High-level scraping and enrichment workflow for planning applications."""

from pathlib import Path

import requests

from ..constants import SCRAPER_CACHE_DIR
from ..models import Application, PlanningQuery
from ..parsing.parser import (
    extract_applications,
    extract_further_information,
    extract_important_dates,
    extract_pagination_urls,
    extract_summary_fields,
)
from .cache import load_cached_applications, save_cached_applications
from .oxford_planning_client import (
    build_dates_tab_url,
    build_further_information_tab_url,
    fetch_form,
    fetch_page,
    fetch_results_page,
)


def enrich_application(
    session: requests.Session,
    application: Application,
    *,
    query: PlanningQuery,
) -> Application:
    """Fetch and attach summary-only fields and important dates.

    Args:
        session: HTTP session used to request the Oxford planning site.
        application: Parsed application to enrich.
        query: Query mode used to decide which extra pages are required.

    Returns:
        The application with summary-only fields, further information, and
        important dates populated when available.
    """
    further_information_html, _ = fetch_page(
        session,
        build_further_information_tab_url(application.url),
    )
    ward, parish = extract_further_information(further_information_html)

    status = None
    decided = None
    decision = None
    if query.status_mode == "decided":
        summary_html, _ = fetch_page(session, application.url)
        status, decided, decision = extract_summary_fields(summary_html)

    consultation_deadline = None
    determination_deadline = None
    if query.status_mode == "validated":
        dates_html, _ = fetch_page(session, build_dates_tab_url(application.url))
        consultation_deadline, determination_deadline = extract_important_dates(
            dates_html
        )

    return Application.model_validate(
        application.model_dump()
        | {
            "ward": ward,
            "parish": parish,
            "status": status,
            "decided": decided,
            "decision": decision,
            "consultation_deadline": consultation_deadline,
            "determination_deadline": determination_deadline,
        }
    )


def filter_applications_by_keywords(
    applications: list[Application], *, query: PlanningQuery
) -> list[Application]:
    """Filter result-card applications to proposal keyword matches when configured."""
    if not query.uses_keyword_matching():
        return applications

    matched_applications: list[Application] = []
    for application in applications:
        keyword_matches = query.matching_keywords(application.proposal)
        if not keyword_matches:
            continue
        matched_applications.append(
            Application.model_validate(
                application.model_dump() | {"keyword_matches": keyword_matches}
            )
        )
    return matched_applications


def collect_result_applications(
    session: requests.Session, *, query: PlanningQuery
) -> list[Application]:
    """Collect applications from the weekly-list results pages before enrichment."""
    csrf_token, weeks = fetch_form(session)
    week = query.selected_week(weeks)
    html, page_url = fetch_results_page(
        session,
        query=query,
        csrf_token=csrf_token,
        week=week,
    )
    applications = extract_applications(html, week, page_url)
    for pagination_url in extract_pagination_urls(html, page_url):
        next_html, next_page_url = fetch_page(session, pagination_url)
        applications.extend(extract_applications(next_html, week, next_page_url))
    return applications


def fetch_latest_applications(query: PlanningQuery) -> list[Application]:
    """Fetch applications for the selected or latest available week.

    Args:
        query: User-facing query options for the weekly list search.

    Returns:
        list of Applications
    """
    session = requests.Session()
    session.headers.update({"User-Agent": "planning-update/0.1"})

    # Proposal text is available on the weekly-list result cards, so keyword
    # matching happens before we hit individual application pages for enrichment.
    applications = collect_result_applications(session, query=query)
    applications = filter_applications_by_keywords(applications, query=query)
    return [
        enrich_application(session, application, query=query)
        for application in applications
    ]


def fetch_latest_applications_cached(
    query: PlanningQuery, *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> list[Application]:
    """Fetch applications for a query, reusing the local cache when available."""
    cached_applications = load_cached_applications(query, cache_dir=cache_dir)
    if cached_applications is not None:
        return cached_applications

    applications = fetch_latest_applications(query)
    save_cached_applications(query, applications, cache_dir=cache_dir)
    return applications


def fetch_applications_for_query(
    *, query: PlanningQuery, debug: bool
) -> list[Application]:
    """Fetch applications, using the local cache for debug runs."""
    if debug:
        return fetch_latest_applications_cached(query)
    return fetch_latest_applications(query)
