"""HTML parsing helpers for the Oxford planning scraper."""

import re
from datetime import date, datetime
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from ..constants import BASE_URL, COMMITTEE_BASE_URL, WEEKLY_LIST_URL
from ..models import (
    APPLICATION_ID_RE,
    Application,
    ApplicationRef,
    CommitteeApplication,
)


def extract_form_values(html: str) -> tuple[str, list[str]]:
    """Extract the CSRF token and available weeks from the weekly-list form.

    Args:
        html: Raw HTML for the weekly-list page.

    Returns:
        A tuple containing the CSRF token and available week labels.
    """
    soup = BeautifulSoup(html, "html.parser")
    csrf_input = soup.select_one("input[name='_csrf']")
    if csrf_input is None or not csrf_input.get("value"):
        raise RuntimeError("Could not find CSRF token on weekly list page.")

    week_options = [
        option.get("value", "").strip()
        for option in soup.select("#week option")
        if option.get("value", "").strip()
    ]
    if not week_options:
        raise RuntimeError("Could not find week options on weekly list page.")

    return csrf_input["value"], week_options


def extract_applications(
    html: str,
    week: str,
    page_url: str | None = None,
) -> list[Application]:
    """Extract planning applications from a weekly results page.

    These are short result cards - will need to go into each application page
    to get full details but we can get a fair amount from the result card
    themselves.

    Args:
        html: Raw HTML returned by the weekly results page.
        week: Week label associated with the HTML response.
        page_url: Final response URL after submitting the weekly-list form.

    Returns:
        Parsed planning applications for the response page.
    """
    soup = BeautifulSoup(html, "html.parser")
    summary_application = extract_summary_application(soup, week, page_url)
    if summary_application is not None:
        return [summary_application]

    search_results = extract_search_result_cards(soup, week)
    if search_results or soup.select_one("#searchResultsContainer, ul#searchresults"):
        return search_results

    message_box = soup.select_one(".messagebox")
    if message_box is not None:
        message_text = normalize_space(message_box.get_text(" ", strip=True)).lower()
        if "no results found" in message_text:
            return []

    anchors = soup.find_all("a", href=True)
    seen_ids: set[str] = set()
    applications: list[Application] = []

    for anchor in anchors:
        application_id = normalize_space(anchor.get_text(" ", strip=True))
        if not APPLICATION_ID_RE.fullmatch(application_id):
            continue
        if application_id in seen_ids:
            continue

        container = find_result_container(anchor)
        proposal = extract_proposal(container)
        application_url = urljoin(BASE_URL, anchor["href"])
        container_text = normalize_space(container.get_text("\n", strip=True))
        address = extract_labeled_value(container_text, "Address") or ""
        received = extract_labeled_value(container_text, "Received")
        validated = extract_labeled_value(container_text, "Validated")
        if received is None or validated is None:
            continue

        applications.append(
            Application(
                application_ref=ApplicationRef(value=application_id),
                proposal=proposal,
                url=application_url,
                address=address,
                received=received,
                validated=validated,
            )
        )
        seen_ids.add(application_id)

    return applications


def extract_pagination_urls(html: str, page_url: str) -> list[str]:
    """Extract additional paginated result URLs from a results page.

    Args:
        html: Raw HTML returned by the weekly results page.
        page_url: Final response URL for the current results page.

    Returns:
        Absolute URLs for additional result pages, excluding the current page.
    """
    soup = BeautifulSoup(html, "html.parser")
    pagination_urls: list[str] = []
    seen_urls: set[str] = set()

    for link in soup.select("p.pager a.page[href]"):
        absolute_url = urljoin(page_url, link["href"])
        if absolute_url == page_url or absolute_url in seen_urls:
            continue
        seen_urls.add(absolute_url)
        pagination_urls.append(absolute_url)

    return pagination_urls


def extract_important_dates(html: str) -> tuple[str | None, str | None]:
    """Extract consultation and determination deadlines from the dates tab.

    Args:
        html: Raw HTML returned by an application's dates tab.

    Returns:
        A tuple of ``(consultation_deadline, determination_deadline)`` date
        strings when present.
    """
    soup = BeautifulSoup(html, "html.parser")
    values = extract_summary_values(soup)

    return (
        values.get("standard consultation expiry date"),
        values.get("determination deadline"),
    )


def extract_major_application_refs(html: str) -> list[ApplicationRef]:
    """Extract application references from Oxford's current major-applications page."""
    soup = BeautifulSoup(html, "html.parser")
    major_heading = soup.find(
        ["h2", "h3"], string=re.compile(r"major applications", re.I)
    )
    if major_heading is None:
        return []

    refs: list[ApplicationRef] = []
    seen_refs: set[str] = set()
    for sibling in major_heading.find_next_siblings():
        if not isinstance(sibling, Tag):
            continue
        if sibling.name in {"h1", "h2"}:
            break

        for anchor in sibling.select("a[href]"):
            raw_ref = normalize_space(anchor.get_text(" ", strip=True))
            if not APPLICATION_ID_RE.fullmatch(raw_ref) or raw_ref in seen_refs:
                continue
            refs.append(ApplicationRef(value=raw_ref))
            seen_refs.add(raw_ref)

    return refs


def extract_future_agenda_urls(
    html: str,
    *,
    today: date,
) -> list[tuple[date, str]]:
    """Extract future planning committee meeting URLs that have an agenda."""
    soup = BeautifulSoup(html, "html.parser")
    meetings: list[tuple[date, str]] = []

    for item in soup.select("li"):
        link = item.select_one("a.mgMeetingTableLnk[href]")
        if link is None:
            continue

        item_text = normalize_space(item.get_text(" ", strip=True))
        if "agenda" not in item_text.lower() or "cancelled" in item_text.lower():
            continue

        meeting_date = parse_committee_meeting_date(
            normalize_space(link.get_text(" ", strip=True))
        )
        if meeting_date is None or meeting_date < today:
            continue

        meetings.append((meeting_date, urljoin(COMMITTEE_BASE_URL, link["href"])))

    return sorted(meetings, key=lambda meeting: meeting[0])


def extract_committee_applications(
    html: str,
    *,
    committee_date: date,
    page_url: str,
) -> list[CommitteeApplication]:
    """Extract application items from a planning committee agenda page."""
    soup = BeautifulSoup(html, "html.parser")
    applications: list[CommitteeApplication] = []
    seen_refs: set[str] = set()

    for row in soup.select("#mgItemTable tr"):
        title_link = row.select_one("a.mgAiTitleLnk[href]")
        if title_link is None:
            continue

        title_text = normalize_space(title_link.get_text(" ", strip=True))
        ref_match = APPLICATION_ID_RE.search(title_text)
        if ref_match is None:
            continue

        application_ref = ref_match.group(0)
        if application_ref in seen_refs:
            continue

        row_text = normalize_space(row.get_text(" ", strip=True))
        address = extract_committee_labeled_value(row_text, "Site address")
        proposal = extract_committee_labeled_value(row_text, "Proposal")
        recommendation = extract_committee_recommendation(row_text)
        if address is None or proposal is None:
            continue

        applications.append(
            CommitteeApplication(
                application_ref=ApplicationRef(value=application_ref),
                committee_date=committee_date,
                proposal=proposal,
                address=address,
                agenda_url=build_absolute_url(page_url, ""),
                report_url=build_absolute_url(page_url, title_link["href"]),
                recommendation=recommendation,
            )
        )
        seen_refs.add(application_ref)

    return applications


def extract_search_result_cards(soup: BeautifulSoup, week: str) -> list[Application]:
    """Extract applications from standard multi-result search result cards.

    Args:
        soup: Parsed HTML document for the response page.
        week: Week label associated with the HTML response.

    Returns:
        Applications parsed from standard search result cards.
    """
    applications: list[Application] = []

    for result in soup.select("li.searchresult"):
        summary_link = result.select_one("a.summaryLink[href]")
        if summary_link is None:
            continue

        proposal = normalize_space(summary_link.get_text(" ", strip=True))
        address = ""
        address_tag = result.select_one("p.address")
        if address_tag is not None:
            address = normalize_space(address_tag.get_text(" ", strip=True))
        meta_info = result.select_one("p.metaInfo")
        if meta_info is None:
            continue

        meta_text = normalize_space(meta_info.get_text(" ", strip=True))
        reference_match = re.search(r"Ref\.\s*No:\s*(\d{2}/\d{5}/[A-Z0-9]+)", meta_text)
        if reference_match is None:
            continue

        application_id = reference_match.group(1)
        received = extract_meta_date(meta_text, "Received")
        validated = extract_meta_date(meta_text, "Validated")
        if received is None or validated is None:
            continue
        raw_status = extract_meta_value(meta_text, "Status")
        applications.append(
            Application(
                application_ref=ApplicationRef(value=application_id),
                proposal=proposal,
                url=urljoin(BASE_URL, summary_link["href"]),
                address=address,
                received=received,
                validated=validated,
                status=raw_status,
            )
        )

    return applications


def extract_summary_fields(
    html: str,
) -> tuple[str | None, str | None, str | None]:
    """Extract summary-only fields from an application's summary page.

    Args:
        html: Raw HTML returned by an application's summary page.

    Returns:
        A tuple of ``(status, decided, decision)`` values when present.
    """
    soup = BeautifulSoup(html, "html.parser")
    values = extract_summary_values(soup)
    if not values:
        return None, None, None

    status = values.get("status")
    decided = values.get("decision issued date")
    decision = values.get("decision")

    return status, decided, decision


def extract_summary_application(
    soup: BeautifulSoup,
    week: str,
    page_url: str | None,
) -> Application | None:
    """Extract a single application from an application summary page.

    Args:
        soup: Parsed HTML document for the response page.
        week: Week label associated with the HTML response.
        page_url: Final response URL after submitting the weekly-list form.

    Returns:
        A parsed application when the page is an application summary, otherwise
        ``None``.
    """
    values = extract_summary_values(soup)
    if not values:
        return None

    application_id = values.get("reference")
    proposal = values.get("proposal", "")
    if application_id is None or not APPLICATION_ID_RE.fullmatch(application_id):
        return None

    summary_link = soup.select_one("a#tab_summary[href], a#subtab_summary[href]")
    application_url = page_url or WEEKLY_LIST_URL
    if summary_link is not None:
        application_url = urljoin(BASE_URL, summary_link["href"])

    received = values.get("application received")
    validated = values.get("application validated")
    if received is None or validated is None:
        return None

    return Application(
        application_ref=ApplicationRef(value=application_id),
        proposal=proposal,
        url=application_url,
        address=values.get("address", ""),
        received=received,
        validated=validated,
        decided=values.get("decision issued date"),
        status=values.get("status"),
        decision=values.get("decision"),
    )


def extract_summary_values(soup: BeautifulSoup) -> dict[str, str]:
    """Extract normalized key/value pairs from an application details table.

    Args:
        soup: Parsed HTML document containing a ``#simpleDetailsTable`` table.

    Returns:
        A mapping of normalized table labels to their text values.
    """
    details_table = soup.select_one("#simpleDetailsTable")
    if details_table is None:
        # Oxford City Council uses #simpleDetailsTable on summary/dates pages, but the
        # Further Information tab renders an unlabelled table inside .tabcontainer.
        # We miss info if we don't try and grab tables like this
        details_table = soup.select_one(".tabcontainer table")
    if details_table is None:
        return {}

    values: dict[str, str] = {}
    for row in details_table.select("tr"):
        label_cell = row.find("th")
        value_cell = row.find("td")
        if label_cell is None or value_cell is None:
            continue
        label = normalize_space(label_cell.get_text(" ", strip=True)).lower()
        value = normalize_space(value_cell.get_text(" ", strip=True))
        if label and value:
            values[label] = value

    return values


def find_result_container(anchor: Tag) -> Tag:
    """Find the nearest result wrapper around an application link.

    Args:
        anchor: Anchor element containing the planning application reference.

    Returns:
        The closest container that appears to hold the full result row or card.
    """
    for parent in anchor.parents:
        if not isinstance(parent, Tag):
            continue
        classes = " ".join(parent.get("class", []))
        if "searchresult" in classes.lower():
            return parent
        if parent.name in {"li", "tr", "article"}:
            return parent
    return anchor


def extract_proposal(container: Tag) -> str:
    """Extract the proposal text from a result container.

    Args:
        container: Result row or card containing planning application details.

    Returns:
        The proposal text if it can be found, otherwise an empty string.
    """
    for label in container.find_all(["dt", "th", "strong", "span"]):
        label_text = normalize_space(label.get_text(" ", strip=True)).rstrip(":")
        if label_text.lower() != "proposal":
            continue

        sibling = label.find_next_sibling()
        while sibling is not None and not normalize_space(
            sibling.get_text(" ", strip=True)
        ):
            sibling = sibling.find_next_sibling()
        if sibling is not None:
            value = normalize_space(sibling.get_text(" ", strip=True))
            if value:
                return value

    text = normalize_space(container.get_text("\n", strip=True))
    proposal_match = re.search(
        r"Proposal:?\s*(.+?)(?:Address:|Status:|Applicant:|Agent:|Ward:|Parish:|Case Officer:|$)",
        text,
        flags=re.IGNORECASE,
    )
    if proposal_match:
        return normalize_space(proposal_match.group(1))

    return ""


def normalize_space(value: str) -> str:
    """Collapse repeated whitespace into single spaces.

    Args:
        value: Input text that may contain irregular whitespace.

    Returns:
        The normalized string with repeated whitespace collapsed.
    """
    return " ".join(value.split())


def build_absolute_url(base_url: str, href: str) -> str:
    """Build an absolute URL and quote spaces in path/query components."""
    absolute_url = urljoin(base_url, href)
    parts = urlsplit(absolute_url)
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            quote(parts.path, safe="/%"),
            quote(parts.query, safe="=&?/%+-_."),
            quote(parts.fragment, safe="=&?/%+-_."),
        )
    )


def extract_labeled_value(text: str, label: str) -> str | None:
    """Extract a labeled value from flattened text.

    Args:
        text: Flattened text containing label/value pairs.
        label: Label to extract, for example ``Address``.

    Returns:
        The extracted value if present, otherwise ``None``.
    """
    match = re.search(
        rf"{label}:?\s*(.+?)(?:Address:|Status:|Applicant:|Agent:|Ward:|Parish:|Case Officer:|Received:|Validated:|Decided:|$)",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return normalize_space(match.group(1))


def parse_committee_meeting_date(value: str) -> date | None:
    """Parse a Modern.Gov committee meeting date label."""
    match = re.search(r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", value)
    if match is None:
        return None
    raw_date = match.group(1)
    for date_format in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw_date, date_format).date()
        except ValueError:
            continue
    return None


def extract_committee_labeled_value(text: str, label: str) -> str | None:
    """Extract labeled agenda item text from a flattened committee row."""
    following_labels = [
        "Site address",
        "Proposal",
        "Reason at Committee",
        "RECOMMENDATION",
        "Oxford City Planning Committee",
    ]
    stops = "|".join(re.escape(item) for item in following_labels if item != label)
    match = re.search(
        rf"{re.escape(label)}\s*:?\s*(.+?)(?:\s+(?:{stops})\s*:?\s*|\s*$)",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return normalize_space(match.group(1))


def extract_committee_recommendation(text: str) -> str | None:
    """Extract a short recommendation from committee agenda item text."""
    recommendation_match = re.search(
        r"\bRECOMMENDATION\b\s*:?\s*(.+)",
        text,
        flags=re.IGNORECASE,
    )
    if recommendation_match is None:
        return None

    recommended_to_match = re.search(
        r"recommended\s+to\b(.+)",
        recommendation_match.group(1),
        flags=re.IGNORECASE,
    )
    candidate_text = (
        recommended_to_match.group(1)
        if recommended_to_match is not None
        else recommendation_match.group(1)
    )
    action_match = re.search(
        r"\b(approve|refuse|grant|defer|note)\b",
        candidate_text,
        flags=re.IGNORECASE,
    )
    if action_match is None:
        return None
    return action_match.group(1).capitalize()


def extract_meta_date(meta_text: str, label: str) -> str | None:
    """Extract a labeled date from search result metadata text.

    Args:
        meta_text: Flattened metadata text from a result card.
        label: Metadata label to extract, for example ``Received``.

    Returns:
        The extracted date string if present, otherwise ``None``.
    """
    match = re.search(rf"{label}:\s*(.+?)(?:\s+\|\s+|$)", meta_text)
    if match is None:
        return None
    return normalize_space(match.group(1))


def extract_meta_value(meta_text: str, label: str) -> str | None:
    """Extract a labeled value from search result metadata text.

    Args:
        meta_text: Flattened metadata text from a result card.
        label: Metadata label to extract.

    Returns:
        The extracted value if present, otherwise ``None``.
    """
    match = re.search(rf"{label}:\s*(.+?)(?:\s+\|\s+|$)", meta_text)
    if match is None:
        return None
    return normalize_space(match.group(1))
