"""Low-level HTTP helpers for the Oxford planning site."""

import logging
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from ..constants import DEFAULT_TIMEOUT_SECONDS, RESULTS_URL, WEEKLY_LIST_URL
from ..models import PlanningQuery
from ..parsing.parser import extract_form_values

logger = logging.getLogger(__name__)


def fetch_form(session: requests.Session) -> tuple[str, list[str]]:
    """Fetch the weekly-list form and extract submission values."""
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
    """Submit the weekly-list search form for a single week."""
    payload = query.build_search_payload(csrf_token=csrf_token, week=week)
    logger.debug("POST %s", RESULTS_URL)
    response = session.post(
        RESULTS_URL,
        data=payload,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text, response.url


def fetch_page(session: requests.Session, page_url: str) -> tuple[str, str]:
    """Fetch a follow-up or paginated page."""
    logger.debug("GET %s", page_url)
    response = session.get(page_url, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text, response.url


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
