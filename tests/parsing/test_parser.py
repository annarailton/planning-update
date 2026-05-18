"""Tests for HTML parsing helpers."""

from datetime import date

import pytest
from bs4 import BeautifulSoup

from planning_update.parsing.parser import (
    extract_committee_applications,
    extract_committee_recommendation,
    extract_form_values,
    extract_future_agenda_urls,
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


@pytest.mark.parametrize(
    ("html", "expected_meetings"),
    [
        pytest.param(
            """
            <ul>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8510&amp;Ver=4">14 Jul 2026&nbsp;6.00 pm</a></li>
            </ul>
            """,
            [],
            id="future-date-without-agenda",
        ),
        pytest.param(
            """
            <ul>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8165&amp;Ver=4">26 May 2026&nbsp;6.00 pm</a> - Agenda</li>
            </ul>
            """,
            [
                (
                    date(2026, 5, 26),
                    "https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=568&MId=8165&Ver=4",
                )
            ],
            id="future-date-with-agenda",
        ),
        pytest.param(
            """
            <ul>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8162&amp;Ver=4">24 Feb 2026&nbsp;6.00 pm</a> - Agenda</li>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8161&amp;Ver=4">20 Jan 2026&nbsp;6.00 pm</a> - Agenda</li>
            </ul>
            """,
            [],
            id="no-future-dates",
        ),
        pytest.param(
            """
            <ul>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8510&amp;Ver=4">14 Jul 2026&nbsp;6.00 pm</a></li>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8165&amp;Ver=4">26 May 2026&nbsp;6.00 pm</a> - Agenda</li>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8163&amp;Ver=4">24 Mar 2026&nbsp;6.00 pm</a> - CANCELLED</li>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8162&amp;Ver=4">24 Feb 2026&nbsp;6.00 pm</a> - Agenda</li>
            </ul>
            """,
            [
                (
                    date(2026, 5, 26),
                    "https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=568&MId=8165&Ver=4",
                )
            ],
            id="mixed-meetings",
        ),
    ],
)
def test_extract_future_agenda_urls_filters_top_level_meetings_page(
    html: str,
    expected_meetings: list[tuple[date, str]],
) -> None:
    """Top-level committee page parsing should return only future agenda URLs."""
    meetings = extract_future_agenda_urls(
        html,
        today=date(2026, 5, 18),
    )

    assert meetings == expected_meetings


def test_extract_committee_applications_reads_agenda_items() -> None:
    """Committee agenda parsing should extract report links and proposal details."""
    applications = extract_committee_applications(
        """
        <table id="mgItemTable">
          <tr>
            <td><p class="mgAiTitleTxt">5.</p></td>
            <td>
              <p class="mgAiTitleTxt"><a class="mgAiTitleLnk" href="documents/s90579/Minutes.pdf">Minutes PDF 154 KB</a></p>
            </td>
          </tr>
          <tr>
            <td><p class="mgAiTitleTxt">6.</p></td>
            <td>
              <p class="mgAiTitleTxt"><a class="mgAiTitleLnk" href="documents/s90588/25-03195-FUL Mansfield College.pdf">25/03195/FUL Mansfield College, Mansfield Road, Oxford, Oxfordshire PDF 896 KB</a></p>
              <p><b>Site address</b>: Mansfield College, Mansfield Road, Oxford, Oxfordshire</p>
              <p><b>Proposal:</b> Demolition of the John Marsh Building and erection of a four storey building.</p>
              <p><b>Reason at Committee:</b> Major Development</p>
              <p><b>RECOMMENDATION</b></p>
              <p>Oxford City Planning Committee is recommended to:</p>
              <p><b>Approve the application</b> for the reasons given in the report.</p>
            </td>
          </tr>
          <tr>
            <td><p class="mgAiTitleTxt">7.</p></td>
            <td>
              <p class="mgAiTitleTxt"><a class="mgAiTitleLnk" href="documents/s90581/2503196LBC - Mansfield College.pdf">25/03196/LBC Mansfield College, Mansfield Road, Oxford, Oxfordshire PDF 718 KB</a></p>
              <p><b>Site address:</b> Mansfield College Mansfield Road Oxford Oxfordshire OX1 3TF</p>
              <p><b>Proposal:</b> Internal and external alterations to the Champneys north range buildings.</p>
              <p><b>Reason at Committee:</b> Concurrent application</p>
              <p><b>RECOMMENDATION</b></p>
              <p>Oxford City Planning Committee is recommended to:</p>
              <p><b>Approve the application</b> for the reasons given in the report.</p>
            </td>
          </tr>
          <tr>
            <td><p class="mgAiTitleTxt">8.</p></td>
            <td>
              <p class="mgAiTitleTxt"><a class="mgAiTitleLnk" href="documents/s90580/25.03223FUL - Cable Burcott Solar Farm.pdf">25/03223/FUL Land At Watlington Road, Cowley, Oxford PDF 605 KB</a></p>
              <p><b>Site address:</b> Land At Watlington Road, Cowley, Oxford</p>
              <p><b>Proposal:</b> Installation of an underground high voltage cable to support solar farm.</p>
              <p><b>Reason at Committee:</b> Major Development</p>
              <p><b>RECOMMENDATION</b></p>
              <p>Oxford City Planning Committee is recommended to:</p>
              <p><b>Approve the application</b> for the reasons given in the report.</p>
            </td>
          </tr>
        </table>
        """,
        committee_date=date(2026, 5, 26),
        page_url="https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=568&MId=8165&Ver=4",
    )

    assert [application.application_ref.value for application in applications] == [
        "25/03195/FUL",
        "25/03196/LBC",
        "25/03223/FUL",
    ]
    assert [application.recommendation for application in applications] == [
        "Approve",
        "Approve",
        "Approve",
    ]
    assert applications[0].committee_date == date(2026, 5, 26)
    assert applications[0].address == (
        "Mansfield College, Mansfield Road, Oxford, Oxfordshire"
    )
    assert applications[0].proposal == (
        "Demolition of the John Marsh Building and erection of a four storey building."
    )
    assert applications[0].agenda_url == (
        "https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=568&MId=8165&Ver=4"
    )
    assert applications[0].report_url == (
        "https://mycouncil.oxford.gov.uk/documents/s90588/25-03195-FUL%20Mansfield%20College.pdf"
    )


def test_extract_committee_applications_reads_refusal_recommendation() -> None:
    """Committee agenda parsing should normalize refusal recommendations."""
    applications = extract_committee_applications(
        """
        <table id="mgItemTable">
          <tr>
            <td><p class="mgAiTitleTxt">43.</p></td>
            <td>
              <p class="mgAiTitleTxt"><a class="mgAiTitleLnk" href="documents/s89123/25-02702-FUL Unit 11 Kings Meadow.pdf">25/02702/FUL Unit 11, Kings Meadow, Ferry Hinksey Road, Oxford PDF 520 KB</a></p>
              <p><b>Site address:</b> Unit 11, Kings Meadow, Ferry Hinksey Road, Oxford</p>
              <p><b>Proposal:</b> Change of use to a day nursery.</p>
              <p><b>Reason at Committee:</b> Called in</p>
              <p><b>RECOMMENDATION</b></p>
              <p>Oxford City Planning Committee is recommended to:</p>
              <p><b>Refuse the application</b> for the reasons given in the report, including flood risk in Flood Zone 3b and inadequate cycle parking.</p>
            </td>
          </tr>
        </table>
        """,
        committee_date=date(2025, 12, 9),
        page_url="https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=568&MId=8160&Ver=4",
    )

    assert len(applications) == 1
    assert applications[0].application_ref.value == "25/02702/FUL"
    assert applications[0].proposal == "Change of use to a day nursery."
    assert applications[0].address == (
        "Unit 11, Kings Meadow, Ferry Hinksey Road, Oxford"
    )
    assert applications[0].recommendation == "Refuse"


@pytest.mark.parametrize(
    ("text", "expected_recommendation"),
    [
        pytest.param(
            (
                "RECOMMENDATION Oxford City Planning Committee is recommended to: "
                "Approve the application for the reasons given in the report."
            ),
            "Approve",
            id="approve",
        ),
        pytest.param(
            (
                "RECOMMENDATION Oxford City Planning Committee is recommended to: "
                "Refuse the application for the reasons given in the report."
            ),
            "Refuse",
            id="refuse",
        ),
        pytest.param(
            "Proposal: Change of use to a day nursery.",
            None,
            id="missing-recommendation",
        ),
        pytest.param(
            "RECOMMENDATION Oxford City Planning Committee is recommended to consider the report.",
            None,
            id="no-known-action",
        ),
    ],
)
def test_extract_committee_recommendation(
    text: str,
    expected_recommendation: str | None,
) -> None:
    """Recommendation parsing should return only known short actions."""
    assert extract_committee_recommendation(text) == expected_recommendation
