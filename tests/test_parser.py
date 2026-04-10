"""Tests for HTML parsing helpers."""

from datetime import date

from bs4 import BeautifulSoup

from parser import (
    extract_further_information,
    extract_search_result_cards,
    extract_summary_application,
    extract_summary_values,
)


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
