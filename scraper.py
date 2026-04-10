"""HTTP and orchestration logic for the Oxford planning application scraper."""

import logging
from typing import Iterable

import requests

from constants import DEFAULT_TIMEOUT_SECONDS, RESULTS_URL, WEEKLY_LIST_URL
from location_lookup import (
    PARISH_CODE_TO_NAME,
    WARD_CODE_TO_NAME,
    resolve_parish_code,
    resolve_ward_code,
)
from models import Application, PlanningQuery
from parser import extract_applications, extract_form_values
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


def fetch_latest_applications(query: PlanningQuery) -> list[Application]:
    """Fetch applications from the first queried week with results.

    Args:
        query: User-facing query options for the weekly list search.

    Returns:
        list of Applications
    """
    session = requests.Session()
    session.headers.update({"User-Agent": "planning-update/0.1"})

    ward_code = resolve_ward_code(query.ward_name)
    resolved_ward_name = WARD_CODE_TO_NAME[ward_code]

    parish_code = ""
    resolved_parish_name = None
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
        if applications:
            return applications
        if query.strict:
            return []
        if query.requested_week is None and index + 1 < len(candidate_weeks):
            target_area = resolved_ward_name
            if resolved_parish_name is not None:
                target_area = f"{resolved_ward_name} / {resolved_parish_name}"
            logger.info(  # pyright: ignore[reportCallIssue]
                f"No results for week {week} in {target_area}, "
                f"falling back to {candidate_weeks[index + 1]}"
            )

    return []
