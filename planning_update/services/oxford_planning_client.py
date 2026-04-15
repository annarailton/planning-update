"""Low-level HTTP helpers for the Oxford planning site."""

import logging
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import backoff
import requests

from ..constants import (
    DEFAULT_TIMEOUT_SECONDS,
    MAJOR_APPLICATIONS_URL,
    RESULTS_URL,
    RETRY_INITIAL_BACKOFF_SECONDS,
    RETRY_MAX_RETRIES,
    RETRY_STATUS_CODES,
    WEEKLY_LIST_URL,
)
from ..models import PlanningQuery
from ..parsing.parser import extract_form_values

logger = logging.getLogger(__name__)


def should_retry_response(response: requests.Response) -> bool:
    """Return whether a response should be retried."""
    return response.status_code in RETRY_STATUS_CODES


def log_backoff(details: dict[str, object]) -> None:
    """Emit a concise retry log line for backoff retries."""
    kwargs = details.get("kwargs", {})
    method = kwargs.get("method", "REQUEST") if isinstance(kwargs, dict) else "REQUEST"
    url = kwargs.get("url", "") if isinstance(kwargs, dict) else ""
    value = details.get("value")
    if isinstance(value, requests.Response):
        outcome = f"status {value.status_code}"
    else:
        exc = details.get("exception")
        outcome = exc.__class__.__name__ if exc is not None else "retry"

    logger.warning(
        "%s %s hit %s, retrying in %.2fs (attempt %s/%s)",
        method,
        url,
        outcome,
        float(details["wait"]),
        int(details["tries"]),
        RETRY_MAX_RETRIES + 1,
    )


def request_with_backoff(
    session: requests.Session,
    *,
    method: str,
    url: str,
    **kwargs,
) -> requests.Response:
    """Send a request with lightweight exponential backoff for transient failures."""

    @backoff.on_exception(
        backoff.expo,
        (requests.ConnectionError, requests.Timeout),
        max_tries=RETRY_MAX_RETRIES + 1,
        factor=RETRY_INITIAL_BACKOFF_SECONDS,
        jitter=backoff.full_jitter,
        on_backoff=log_backoff,
    )
    # Some responses may have retry-worthy status codes, but we need to
    # inspect the response before deciding whether to raise for status or retry
    @backoff.on_predicate(
        backoff.expo,
        predicate=should_retry_response,
        max_tries=RETRY_MAX_RETRIES + 1,
        factor=RETRY_INITIAL_BACKOFF_SECONDS,
        jitter=backoff.full_jitter,
        on_backoff=log_backoff,
    )
    def send_request() -> requests.Response:
        response = session.request(method, url, **kwargs)
        if response.status_code >= 400 and not should_retry_response(response):
            response.raise_for_status()
        return response

    response = send_request()
    if should_retry_response(response):
        response.raise_for_status()
    return response


def fetch_form(session: requests.Session) -> tuple[str, list[str]]:
    """Fetch the weekly-list form and extract submission values."""
    response = request_with_backoff(
        session,
        method="GET",
        url=WEEKLY_LIST_URL,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    return extract_form_values(response.text)


def fetch_results_page(
    session: requests.Session,
    *,
    query: PlanningQuery,
    csrf_token: str,
    week: str,
) -> tuple[str, str]:
    """Submit the weekly-list search form for a single week."""
    payload = query.build_search_payload(csrf_token=csrf_token, week=week)
    logger.debug("POST %s", RESULTS_URL)
    response = request_with_backoff(
        session,
        method="POST",
        url=RESULTS_URL,
        data=payload,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    return response.text, response.url


def fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
    """Fetch a follow-up or paginated page."""
    logger.debug("GET %s", page_url)
    response = request_with_backoff(
        session,
        method="GET",
        url=page_url,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    return response.text, response.url


def fetch_major_applications_page(session: requests.Session) -> str:
    """Fetch the Oxford City Council page listing current major applications."""
    response = request_with_backoff(
        session,
        method="GET",
        url=MAJOR_APPLICATIONS_URL,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    return response.text


def resolve_actual_week(query: PlanningQuery) -> str:
    """Resolve the actual week label a query would use from the live weekly form."""
    session = requests.Session()
    session.headers.update({"User-Agent": "planning-update/0.1"})
    _, weeks = fetch_form(session)
    return query.selected_week(weeks)


def build_dates_tab_url(application_url: str) -> str:
    """Build the dates-tab URL for a planning application."""
    parsed_url = urlparse(application_url)
    query_params = parse_qs(parsed_url.query)
    query_params["activeTab"] = ["dates"]
    return urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True)))


def build_further_information_tab_url(application_url: str) -> str:
    """Build the further-information-tab URL for a planning application."""
    parsed_url = urlparse(application_url)
    query_params = parse_qs(parsed_url.query)
    query_params["activeTab"] = ["details"]
    return urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True)))
