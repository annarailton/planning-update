"""Scraping workflow for Coming to next planning committee agenda applications."""

from datetime import date

import requests

from ..models import CommitteeApplication
from ..parsing.parser import extract_committee_applications, extract_future_agenda_urls
from .oxford_planning_client import (
    fetch_planning_committee_agenda_page,
    fetch_planning_committee_meetings_page,
)


def current_date() -> date:
    """Return the current local date for selecting future committee meetings."""
    return date.today()


def fetch_upcoming_committee_applications(
    *,
    today: date | None = None,
) -> list[CommitteeApplication]:
    """Fetch applications from the next future Planning Committee agenda."""
    render_today = today or current_date()
    session = requests.Session()
    session.headers.update({"User-Agent": "planning-update/0.1"})

    meetings_html = fetch_planning_committee_meetings_page(session)
    future_agenda_urls = extract_future_agenda_urls(
        meetings_html,
        today=render_today,
    )
    for committee_date, agenda_url in future_agenda_urls:
        agenda_html, page_url = fetch_planning_committee_agenda_page(
            session,
            agenda_url,
        )
        applications = extract_committee_applications(
            agenda_html,
            committee_date=committee_date,
            page_url=page_url,
        )
        if applications:
            return applications

    return []
