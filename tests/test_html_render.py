"""Tests for HTML rendering of planning applications."""

from datetime import date, datetime

import pytest

import html_render
from models import Application, ApplicationRef


def build_application(
    *,
    decision: str,
    consultation_deadline: date = date(2026, 3, 16),
    determination_deadline: date = date(2026, 4, 6),
    status: str = "Decided",
) -> Application:
    """Build an application fixture for HTML rendering tests."""
    return Application(
        application_ref=ApplicationRef(value="26/00281/FUL"),
        proposal="Test proposal",
        url="https://example.com/app",
        address="1 Test Street",
        ward="Churchill Ward",
        parish=None,
        received=date(2026, 2, 2),
        validated=date(2026, 2, 9),
        decided=date(2026, 4, 9),
        consultation_deadline=consultation_deadline,
        determination_deadline=determination_deadline,
        status=status,
        decision=decision,
    )


@pytest.mark.parametrize(
    ("decision", "css_class", "css_rule"),
    [
        (
            "Approved",
            "field-value--decision-approved",
            ".field-value--decision-approved{color:var(--color-success);",
        ),
        (
            "Prior approval not required",
            "field-value--decision-approved",
            ".field-value--decision-approved{color:var(--color-success);",
        ),
        (
            "Rejected",
            "field-value--decision-rejected",
            ".field-value--decision-rejected{color:var(--color-danger);",
        ),
    ],
)
def test_render_application_html_colours_decisions(
    decision: str, css_class: str, css_rule: str
) -> None:
    """Decision values should use the expected styling."""
    html = html_render.render_application_html([build_application(decision=decision)])

    assert css_rule in html
    assert f'<td class="field-value {css_class}" valign="top">{decision}</td>' in html


@pytest.mark.parametrize(
    ("field_name", "field_value", "css_class", "css_rule"),
    [
        (
            "consultation_deadline",
            date(2026, 4, 20),
            "field-value--date-future",
            ".field-value--date-future{color:var(--color-success);",
        ),
        (
            "consultation_deadline",
            date(2026, 4, 10),
            "field-value--date-past",
            ".field-value--date-past{color:var(--color-danger);",
        ),
        (
            "determination_deadline",
            date(2026, 4, 20),
            "field-value--date-future",
            ".field-value--date-future{color:var(--color-success);",
        ),
        (
            "determination_deadline",
            date(2026, 4, 10),
            "field-value--date-past",
            ".field-value--date-past{color:var(--color-danger);",
        ),
    ],
)
def test_render_application_html_colours_deadlines(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    field_value: date,
    css_class: str,
    css_rule: str,
) -> None:
    """Deadline values should use the expected future or past styling."""
    monkeypatch.setattr(html_render, "current_date", lambda: date(2026, 4, 13))

    html = html_render.render_application_html(
        [build_application(decision="Approved", **{field_name: field_value})]
    )

    assert css_rule in html
    assert (
        f'<td class="field-value {css_class}" valign="top">{field_value.isoformat()}</td>'
        in html
    )


@pytest.mark.parametrize(
    ("status", "css_class", "css_rule"),
    [
        (
            "Decided",
            "field-value--status-decided",
            ".field-value--status-decided{color:var(--color-success);",
        ),
        (
            "Registered",
            "field-value--status-registered",
            ".field-value--status-registered{color:var(--color-warning);",
        ),
    ],
)
def test_render_application_html_colours_statuses(
    status: str, css_class: str, css_rule: str
) -> None:
    """Status values should use the expected styling."""
    html = html_render.render_application_html(
        [build_application(decision="Approved", status=status)]
    )

    assert css_rule in html
    assert f'<td class="field-value {css_class}" valign="top">{status}</td>' in html


def test_render_application_html_colours_past_decision_dates_green(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Past decision dates should use the success styling."""
    monkeypatch.setattr(html_render, "current_date", lambda: date(2026, 4, 13))

    html = html_render.render_application_html([build_application(decision="Approved")])

    assert "--color-success:#18794e;" in html
    assert "--color-warning:#b26b00;" in html
    assert "--color-danger:#c81e1e;" in html
    assert "--color-link:#0b6e4f;" in html
    assert ".field-value--decision-date-past{color:var(--color-success);" in html
    assert (
        '<td class="field-value field-value--decision-date-past" valign="top">2026-04-09</td>'
        in html
    )


def test_render_application_html_shows_search_criteria_in_header() -> None:
    """The HTML output should include the search criteria used."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        html_render, "current_datetime", lambda: datetime(2026, 4, 13, 9, 30)
    )
    try:
        html = html_render.render_application_html(
            [build_application(decision="Approved")],
            search_criteria={
                "Ward": "Churchill",
                "Parish": "All parishes",
                "Mode": "Decided in this week",
                "Week": "30 Mar 2026",
                "Fallback weeks": "1",
                "Strict mode": "Yes",
            },
        )
    finally:
        monkeypatch.undo()

    assert "Search criteria" in html
    assert 'class="criteria-list"' in html
    assert "Generated 2026-04-13 09:30" in html
    assert "Ward:" in html
    assert "Churchill" in html
    assert "Mode:" in html
    assert "Decided in this week" in html
