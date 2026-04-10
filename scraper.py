"""HTTP and orchestration logic for the Oxford planning application scraper."""

import logging
from typing import Iterable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from constants import DEFAULT_TIMEOUT_SECONDS, RESULTS_URL, WEEKLY_LIST_URL
from location_lookup import (
    PARISH_CODE_TO_NAME,
    WARD_CODE_TO_NAME,
    resolve_parish_code,
    resolve_ward_code,
)
from models import Application, PlanningQuery
from parser import (
    extract_applications,
    extract_form_values,
    extract_important_dates,
    extract_pagination_urls,
    extract_summary_fields,
)
from query import build_search_payload

logger = logging.getLogger(__name__)


def fetch_form(session: requests.Session) -> tuple[str, list[str]]:
    """Fetch the weekly-list form and extract submission values.

    Args:
        session: HTTP session used to request the Oxford planning site.

    Returns:
        A tuple containing the CSRF token and available week labels.
    """
    response = session.get(WEEKLY_LIST_URL, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    return extract_form_values(response.text)


def fetch_results_page(
    session: requests.Session,
    *,
    csrf_token: str,
    week: str,
    ward_code: str,
    parish_code: str = "",
    status_mode: str = "validated",
) -> tuple[str, str]:
    """Submit the weekly-list search form for a single week.

    Args:
        session: HTTP session used to request the Oxford planning site.
        csrf_token: CSRF token extracted from the weekly-list form.
        week: Exact week label from the weekly-list dropdown.
        ward_code: Ward code submitted to the Oxford weekly-list form.
        parish_code: Optional parish code submitted to the Oxford weekly-list form.
        status_mode: Which weekly-list toggle to use: ``validated`` or ``decided``.

    Returns:
        A tuple containing the HTML body and final response URL.
    """
    payload = build_search_payload(
        csrf_token=csrf_token,
        week=week,
        ward_code=ward_code,
        parish_code=parish_code,
        status_mode=status_mode,
    )
    response = session.post(
        RESULTS_URL,
        data=payload,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text, response.url


def fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
    """Fetch a paginated search-results page.

    Args:
        session: HTTP session used to request the Oxford planning site.
        page_url: Absolute or relative URL for the target page.

    Returns:
        A tuple containing the HTML body and final response URL.
    """
    response = session.get(page_url, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text, response.url


def build_dates_tab_url(application_url: str) -> str:
    """Build the dates-tab URL for a planning application.

    Args:
        application_url: Application details URL for a planning application.

    Returns:
        URL for the application's dates tab.
    """
    parsed_url = urlparse(application_url)
    query_params = parse_qs(parsed_url.query)
    query_params["activeTab"] = ["dates"]
    return urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True)))


def enrich_application(
    session: requests.Session,
    application: Application,
) -> Application:
    """Fetch and attach summary-only fields and important dates.

    Args:
        session: HTTP session used to request the Oxford planning site.
        application: Parsed application to enrich.

    Returns:
        The application with summary-only fields and important dates populated
        when available.
    """
    summary_html, _ = fetch_page(session, application.url)
    status, decided, decision = extract_summary_fields(summary_html)
    dates_html, _ = fetch_page(session, build_dates_tab_url(application.url))
    consultation_deadline, determination_deadline = extract_important_dates(dates_html)
    return Application.model_validate(
        application.model_dump()
        | {
            "status": status,
            "decided": decided,
            "decision": decision,
            "consultation_deadline": consultation_deadline,
            "determination_deadline": determination_deadline,
        }
    )


def fetch_latest_applications(query: PlanningQuery) -> list[Application]:
    """Fetch applications from the first queried week with results.

    Args:
        query: User-facing query options for the weekly list search.

    Returns:
        list of Applications
    """
    session = requests.Session()
    session.headers.update({"User-Agent": "planning-update/0.1"})

    ward_code = ""
    resolved_ward_name = "All wards"
    if query.ward_name:
        ward_code = resolve_ward_code(query.ward_name)
        resolved_ward_name = WARD_CODE_TO_NAME[ward_code]

    parish_code = ""
    resolved_parish_name = "All parishes"
    if query.parish_name:
        parish_code = resolve_parish_code(query.parish_name)
        resolved_parish_name = PARISH_CODE_TO_NAME[parish_code]

    csrf_token, weeks = fetch_form(session)

    candidate_weeks: Iterable[str]
    if query.requested_week is not None:
        candidate_weeks = [query.requested_week]
    else:
        candidate_weeks = weeks[: max(1, query.fallback_weeks + 1)]

    for index, week in enumerate(candidate_weeks):
        html, page_url = fetch_results_page(
            session,
            csrf_token=csrf_token,
            week=week,
            ward_code=ward_code,
            parish_code=parish_code,
            status_mode=query.status_mode,
        )
        applications = extract_applications(html, week, page_url)
        for pagination_url in extract_pagination_urls(html, page_url):
            next_html, next_page_url = fetch_page(session, pagination_url)
            applications.extend(extract_applications(next_html, week, next_page_url))
        applications = [
            enrich_application(session, application) for application in applications
        ]
        if applications:
            return applications
        if query.strict:
            return []
        if query.requested_week is None and index + 1 < len(candidate_weeks):
            target_area = resolved_ward_name
            if query.parish_name:
                target_area = f"{resolved_ward_name} / {resolved_parish_name}"
            logger.info(  # pyright: ignore[reportCallIssue]
                f"No results for week {week} in {target_area}, "
                f"falling back to {candidate_weeks[index + 1]}"
            )

    return []
