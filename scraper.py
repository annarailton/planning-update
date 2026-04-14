"""HTTP and orchestration logic for the Oxford planning application scraper."""

from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from cache import load_cached_applications, save_cached_applications
from constants import (
    DEFAULT_TIMEOUT_SECONDS,
    RESULTS_URL,
    SCRAPER_CACHE_DIR,
    WEEKLY_LIST_URL,
)
from models import Application, PlanningQuery
from parser import (
    extract_applications,
    extract_form_values,
    extract_further_information,
    extract_important_dates,
    extract_pagination_urls,
    extract_summary_fields,
)


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
    query: PlanningQuery,
    csrf_token: str,
    week: str,
) -> tuple[str, str]:
    """Submit the weekly-list search form for a single week.

    Args:
        session: HTTP session used to request the Oxford planning site.
        query: User-facing query options for the weekly list search.
        csrf_token: CSRF token extracted from the weekly-list form.
        week: Exact week label from the weekly-list dropdown.

    Returns:
        A tuple containing the HTML body and final response URL.
    """
    payload = query.build_search_payload(csrf_token=csrf_token, week=week)
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


def build_further_information_tab_url(application_url: str) -> str:
    """Build the further-information-tab URL for a planning application.

    Args:
        application_url: Application details URL for a planning application.

    Returns:
        URL for the application's further information tab.
    """
    parsed_url = urlparse(application_url)
    query_params = parse_qs(parsed_url.query)
    query_params["activeTab"] = ["details"]
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
        The application with summary-only fields, further information, and
        important dates populated when available.
    """
    summary_html, _ = fetch_page(session, application.url)
    status, decided, decision = extract_summary_fields(summary_html)
    further_information_html, _ = fetch_page(
        session,
        build_further_information_tab_url(application.url),
    )
    ward, parish = extract_further_information(further_information_html)
    dates_html, _ = fetch_page(session, build_dates_tab_url(application.url))
    consultation_deadline, determination_deadline = extract_important_dates(dates_html)
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
    return [enrich_application(session, application) for application in applications]


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
            | {"keyword_matches": keyword_matches or None}
        )

    return [merged[application_ref] for application_ref in ordered_refs]
