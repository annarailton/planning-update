"""Tests for planning committee agenda scraping."""

from datetime import date

import pytest

from planning_update.services.committee import (
    fetch_upcoming_committee_applications,
    fetch_upcoming_review_committee_applications,
)


@pytest.mark.parametrize(
    ("meetings_html", "expected_agenda_urls", "expected_refs"),
    [
        pytest.param(
            """
            <ul>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8510&amp;Ver=4">14 Jul 2026&nbsp;6.00 pm</a></li>
            </ul>
            """,
            [],
            [],
            id="future-date-without-agenda-no-action",
        ),
        pytest.param(
            """
            <ul>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8165&amp;Ver=4">26 May 2026&nbsp;6.00 pm</a> - Agenda</li>
            </ul>
            """,
            [
                "https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=568&MId=8165&Ver=4"
            ],
            ["25/03195/FUL"],
            id="future-date-with-agenda-action",
        ),
        pytest.param(
            """
            <ul>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8162&amp;Ver=4">24 Feb 2026&nbsp;6.00 pm</a> - Agenda</li>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8161&amp;Ver=4">20 Jan 2026&nbsp;6.00 pm</a> - Agenda</li>
            </ul>
            """,
            [],
            [],
            id="no-future-dates-no-action",
        ),
        pytest.param(
            """
            <ul>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8510&amp;Ver=4">14 Jul 2026&nbsp;6.00 pm</a></li>
              <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=568&amp;MId=8165&amp;Ver=4">26 May 2026&nbsp;6.00 pm</a> - Agenda</li>
            </ul>
            """,
            [
                "https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=568&MId=8165&Ver=4"
            ],
            ["25/03195/FUL"],
            id="mixed-future-meetings-only-agenda-action",
        ),
    ],
)
def test_fetch_upcoming_committee_applications_acts_only_for_future_agendas(
    monkeypatch: pytest.MonkeyPatch,
    meetings_html: str,
    expected_agenda_urls: list[str],
    expected_refs: list[str],
) -> None:
    """Top-level committee page scraping should fetch only future agenda pages."""
    fetched_agendas: list[str] = []

    monkeypatch.setattr(
        "planning_update.services.committee.fetch_planning_committee_meetings_page",
        lambda session: meetings_html,
    )

    def fake_fetch_agenda(session, agenda_url: str) -> tuple[str, str]:
        if not expected_agenda_urls:
            raise AssertionError("No agenda page should have been fetched")
        fetched_agendas.append(agenda_url)
        return (
            """
            <table id="mgItemTable">
              <tr>
                <td><p class="mgAiTitleTxt">6.</p></td>
                <td>
                  <p class="mgAiTitleTxt"><a class="mgAiTitleLnk" href="documents/s90588/report.pdf">25/03195/FUL Mansfield College PDF 896 KB</a></p>
                  <p><b>Site address:</b> Mansfield College, Mansfield Road, Oxford</p>
                  <p><b>Proposal:</b> Demolition and replacement building.</p>
                  <p><b>Reason at Committee:</b> Major Development</p>
                  <p><b>RECOMMENDATION</b></p>
                  <p>Oxford City Planning Committee is recommended to:</p>
                  <p><b>Approve the application</b> for the reasons given in the report.</p>
                </td>
              </tr>
            </table>
            """,
            agenda_url,
        )

    monkeypatch.setattr(
        "planning_update.services.committee.fetch_planning_committee_agenda_page",
        fake_fetch_agenda,
    )

    applications = fetch_upcoming_committee_applications(today=date(2026, 5, 18))

    assert fetched_agendas == expected_agenda_urls
    assert [application.application_ref.value for application in applications] == [
        *expected_refs,
    ]
    assert [application.recommendation for application in applications] == [
        "Approve" for _ in expected_refs
    ]


def test_fetch_upcoming_review_committee_applications_uses_review_meetings_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Planning review committee scraping should use the review meetings list."""
    meetings_html = """
    <ul>
      <li><a class="mgMeetingTableLnk" href="ieListDocuments.aspx?CId=147&amp;MId=9000&amp;Ver=4">26 May 2026&nbsp;6.00 pm</a> - Agenda</li>
    </ul>
    """
    fetched_agendas: list[str] = []

    monkeypatch.setattr(
        "planning_update.services.committee.fetch_planning_review_committee_meetings_page",
        lambda session: meetings_html,
    )

    def fake_fetch_agenda(session, agenda_url: str) -> tuple[str, str]:
        fetched_agendas.append(agenda_url)
        return (
            """
            <table id="mgItemTable">
              <tr>
                <td>
                  <p><a class="mgAiTitleLnk" href="documents/review-report.pdf">25/03195/FUL Review report</a></p>
                  <p><b>Site address:</b> Town Hall, Oxford</p>
                  <p><b>Proposal:</b> Review committee proposal.</p>
                  <p><b>RECOMMENDATION</b></p>
                  <p><b>Approve the application</b></p>
                </td>
              </tr>
            </table>
            """,
            agenda_url,
        )

    monkeypatch.setattr(
        "planning_update.services.committee.fetch_planning_committee_agenda_page",
        fake_fetch_agenda,
    )

    applications = fetch_upcoming_review_committee_applications(today=date(2026, 5, 18))

    assert fetched_agendas == [
        "https://mycouncil.oxford.gov.uk/ieListDocuments.aspx?CId=147&MId=9000&Ver=4"
    ]
    assert [application.application_ref.value for application in applications] == [
        "25/03195/FUL"
    ]
