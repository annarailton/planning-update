"""Tests for HTML parsing helpers."""

from datetime import date

from bs4 import BeautifulSoup

from planning_update.parsing.parser import (
    extract_form_values,
    extract_further_information,
    extract_major_application_refs,
    extract_search_result_cards,
    extract_summary_application,
    extract_summary_values,
)


def test_extract_form_values_reads_week_options_from_weekly_list_page() -> None:
    """Weekly-list parsing should extract the CSRF token and available weeks."""
    csrf_token, weeks = extract_form_values(
        """
        <form>
          <input type="hidden" name="_csrf" value="csrf-123" />
          <select id="week" name="week">
            <option value="">Select one</option>
            <option value="13 Apr 2026">13 Apr 2026</option>
            <option value="06 Apr 2026">06 Apr 2026</option>
          </select>
        </form>
        """
    )

    assert csrf_token == "csrf-123"
    assert weeks == ["13 Apr 2026", "06 Apr 2026"]


def test_extract_search_result_cards_leaves_summary_only_fields_empty() -> None:
    """Search result cards should not populate summary-only decision fields."""
    soup = BeautifulSoup(
        """
        <ul id="searchresults">
          <li class="searchresult">
            <a class="summaryLink" href="/online-applications/applicationDetails.do?activeTab=summary&keyVal=ABC123">
              Demo proposal
            </a>
            <p class="address">1 Test Street</p>
            <p class="metaInfo">
              Ref. No: 26/00281/FUL | Received: Thu 12 Mar 2026 | Validated: Fri 13 Mar 2026 | Status: Registered
            </p>
          </li>
        </ul>
        """,
        "html.parser",
    )

    applications = extract_search_result_cards(soup, "30 Mar 2026")

    assert len(applications) == 1
    assert applications[0].status == "Registered"
    assert applications[0].decided is None
    assert applications[0].decision is None


def test_extract_summary_application_populates_decision_fields() -> None:
    """Summary pages should provide decision date and decision outcome."""
    soup = BeautifulSoup(
        """
        <a id="tab_summary" href="/online-applications/applicationDetails.do?activeTab=summary&keyVal=ABC123">
          Summary
        </a>
        <table id="simpleDetailsTable">
          <tr><th>Reference</th><td>26/00281/FUL</td></tr>
          <tr><th>Proposal</th><td>Demo proposal</td></tr>
          <tr><th>Address</th><td>1 Test Street</td></tr>
          <tr><th>Application Received</th><td>Thu 12 Mar 2026</td></tr>
          <tr><th>Application Validated</th><td>Fri 13 Mar 2026</td></tr>
          <tr><th>Status</th><td>Awaiting decision</td></tr>
          <tr><th>Decision</th><td>Refused</td></tr>
          <tr><th>Decision Issued Date</th><td>Sat 14 Mar 2026</td></tr>
        </table>
        """,
        "html.parser",
    )

    application = extract_summary_application(
        soup,
        "30 Mar 2026",
        "https://public.oxford.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal=ABC123",
    )

    assert application is not None
    assert application.status == "Awaiting decision"
    assert application.decision == "Refused"
    assert application.decided == date(2026, 3, 14)


def test_extract_further_information_returns_ward_and_parish() -> None:
    """Further information pages should provide ward and parish values."""
    ward, parish = extract_further_information(
        """
        <table id="simpleDetailsTable">
          <tr><th>Ward</th><td>Churchill Ward</td></tr>
          <tr><th>Parish</th><td>Littlemore Parish Council</td></tr>
        </table>
        """
    )

    assert ward == "Churchill Ward"
    assert parish == "Littlemore Parish Council"


def test_extract_summary_values_supports_details_table_without_id() -> None:
    """Details pages should be parsed even when the table has no simpleDetailsTable id."""
    soup = BeautifulSoup(
        """
        <div class="tabcontainer">
          <table>
            <tr><th scope="row">Parish</th><td/></tr>
            <tr><th scope="row">Ward</th><td>Churchill Ward</td></tr>
          </table>
        </div>
        """,
        "html.parser",
    )

    assert extract_summary_values(soup) == {"ward": "Churchill Ward"}


def test_extract_major_application_refs_reads_refs_from_major_section() -> None:
    """Major-applications page parsing should return unique application refs."""
    refs = extract_major_application_refs(
        """
        <h2>Major applications</h2>
        <h3><a href="/app/1">26/00266/FUL</a> - Plots 23-26 Oxford Science Park</h3>
        <p>First description.</p>
        <h3><a href="/app/2">25/03242/FUL</a> - 25 Wellington Square</h3>
        <p>Second description.</p>
        <h2>Was this webpage helpful?</h2>
        <h3><a href="/app/3">24/00001/FUL</a> - Ignored later section</h3>
        """
    )

    assert [ref.value for ref in refs] == [
        "26/00266/FUL",
        "25/03242/FUL",
    ]
