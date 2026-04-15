"""Tests for HTML rendering of planning applications."""

from collections.abc import Callable
from datetime import date, datetime

import pytest

from planning_update.models import (
    Application,
    ApplicationSection,
    PlanningQuery,
    ResolvedCliOptions,
)
from planning_update.renderers import html_render


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
        (
            "Application Withdrawn",
            "field-value--decision-rejected",
            ".field-value--decision-rejected{color:var(--color-danger);",
        ),
    ],
)
def test_render_application_html_colours_decisions(
    application_factory: Callable[..., Application],
    decision: str,
    css_class: str,
    css_rule: str,
) -> None:
    """Decision values should use the expected styling."""
    html = html_render.render_application_html([application_factory(decision=decision)])

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
    application_factory: Callable[..., Application],
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    field_value: date,
    css_class: str,
    css_rule: str,
) -> None:
    """Deadline values should use the expected future or past styling."""
    monkeypatch.setattr(html_render, "current_date", lambda: date(2026, 4, 13))

    html = html_render.render_application_html(
        [application_factory(decision="Approved", **{field_name: field_value})]
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
    application_factory: Callable[..., Application],
    status: str,
    css_class: str,
    css_rule: str,
) -> None:
    """Status values should use the expected styling."""
    html = html_render.render_application_html(
        [application_factory(decision="Approved", status=status)]
    )

    assert css_rule in html
    assert f'<td class="field-value {css_class}" valign="top">{status}</td>' in html


def test_render_application_html_colours_past_decision_dates_green(
    application_factory: Callable[..., Application],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Past decision dates should use the success styling."""
    monkeypatch.setattr(html_render, "current_date", lambda: date(2026, 4, 13))

    html = html_render.render_application_html(
        [application_factory(decision="Approved")]
    )

    assert "--color-success:#18794e;" in html
    assert "--color-warning:#b26b00;" in html
    assert "--color-danger:#c81e1e;" in html
    assert "--color-link:#0b6e4f;" in html
    assert ".field-value--decision-date-past{color:var(--color-success);" in html
    assert (
        '<td class="field-value field-value--decision-date-past" valign="top">2026-04-09</td>'
        in html
    )


def test_build_search_criteria_includes_keywords_and_major_from_all_queries() -> None:
    """Search criteria should summarize the full resolved query set."""
    search_criteria = html_render.build_search_criteria(
        options=ResolvedCliOptions(
            status_mode="both",
            queries=[
                PlanningQuery(
                    ward_name="churchill",
                    requested_week="30 Mar 2026",
                    status_mode="validated",
                ),
                PlanningQuery(
                    keywords=["photovoltaics", "heat pump"],
                    requested_week="30 Mar 2026",
                    status_mode="validated",
                ),
                PlanningQuery(
                    major=True,
                    requested_week="30 Mar 2026",
                    status_mode="validated",
                ),
            ],
        ),
    )

    assert search_criteria == {
        "Ward": "Churchill Ward",
        "Parish": "All parishes",
        "Mode": "Validated and decided in this week",
        "Week": "30 Mar 2026",
        "Keywords": "photovoltaics, heat pump",
        "Major applications": "Yes",
    }


def test_build_search_criteria_prefers_actual_week_when_available() -> None:
    """Search criteria should show the actual selected week from the live query."""
    search_criteria = html_render.build_search_criteria(
        options=ResolvedCliOptions(
            status_mode="validated",
            queries=[
                PlanningQuery(
                    ward_name="churchill",
                    status_mode="validated",
                ),
            ],
        ),
        actual_week="07 Apr 2026",
    )

    assert search_criteria["Week"] == "07 Apr 2026"


def test_render_application_html_shows_search_criteria_in_header(
    application_factory: Callable[..., Application],
) -> None:
    """The HTML output should include the search criteria used."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        html_render, "current_datetime", lambda: datetime(2026, 4, 13, 9, 30)
    )
    try:
        html = html_render.render_application_html(
            [application_factory(decision="Approved")],
            search_criteria=html_render.build_search_criteria(
                options=ResolvedCliOptions(
                    status_mode="decided",
                    queries=[
                        PlanningQuery(
                            ward_name="churchill",
                            requested_week="30 Mar 2026",
                            status_mode="decided",
                        ),
                        PlanningQuery(
                            keywords=["photovoltaics", "heat pump"],
                            requested_week="30 Mar 2026",
                            status_mode="decided",
                        ),
                        PlanningQuery(
                            major=True,
                            requested_week="30 Mar 2026",
                            status_mode="validated",
                        ),
                    ],
                ),
            ),
        )
    finally:
        monkeypatch.undo()

    assert "Search criteria" in html
    assert 'class="criteria-list"' in html
    assert '<h2 class="section-title">Search criteria</h2>' in html
    assert "Generated 2026-04-13 09:30" in html
    assert "Ward:" in html
    assert "Churchill" in html
    assert "Mode:" in html
    assert "Decided in this week" in html
    assert "Keywords:" in html
    assert "photovoltaics, heat pump" in html
    assert "Major applications:" in html
    assert "Yes" in html
    assert (
        ".criteria{background:var(--color-surface-primary);border:1px solid var(--color-border-subtle);border-radius:12px;box-shadow:0 4px 12px var(--color-shadow);margin-top:12px;}"
        in html
    )
    assert html.index("View application") < html.index("Search criteria")


def test_render_application_html_shows_keyword_matches(
    application_factory: Callable[..., Application],
) -> None:
    """The HTML output should show matched proposal keywords when present."""
    html = html_render.render_application_html(
        [application_factory(keyword_matches=["heat pump", "pv"])]
    )

    assert "Keyword match" in html
    assert "heat pump, pv" in html


def test_render_application_html_colours_keyword_matches_green(
    application_factory: Callable[..., Application],
) -> None:
    """Keyword match values should use the success styling when present."""
    html = html_render.render_application_html(
        [application_factory(keyword_matches=["heat pump", "pv"])]
    )

    assert ".field-value--keyword-match{color:var(--color-success);" in html
    assert (
        '<td class="field-value field-value--keyword-match" valign="top">heat pump, pv</td>'
        in html
    )


def test_render_application_html_colours_major_applications_green(
    application_factory: Callable[..., Application],
) -> None:
    """Major application values should use the success styling when present."""
    html = html_render.render_application_html(
        [application_factory(is_major_application=True)]
    )

    assert ".field-value--major-application{color:var(--color-success);" in html
    assert (
        '<td class="field-value field-value--major-application" valign="top">Yes</td>'
        in html
    )


def test_render_application_html_shows_empty_card_for_empty_results() -> None:
    """The HTML output should render an empty-state card when no applications exist."""
    html = html_render.render_application_html([])

    assert "No applications" in html
    assert "card--empty" in html


def test_render_application_html_shows_empty_card_for_empty_section() -> None:
    """The HTML output should render an empty-state card for empty named sections."""
    html = html_render.render_application_html(
        [],
        sections=[
            ApplicationSection(title="Validated applications", applications=[]),
            ApplicationSection(
                title="Decided applications",
                applications=[],
                empty_state_message="Not searched",
            ),
        ],
    )

    assert "Validated applications" in html
    assert "Decided applications" in html
    assert "No applications" in html
    assert "Not searched" in html


def test_render_application_html_shows_section_notice_under_header() -> None:
    """Section notices should render directly below the section title."""
    html = html_render.render_application_html(
        [],
        sections=[
            ApplicationSection(
                title="Validated applications",
                applications=[],
                major_apps_notice_message="There are NO major applications validated this week",
            ),
        ],
    )

    assert (
        '<h2 class="section-title">Validated applications</h2>'
        '<p class="section-notice">There are NO major applications validated this week</p>'
        in html
    )


def test_render_application_html_renders_both_empty_sections() -> None:
    """The HTML output should render both sections when both-mode has no results."""
    html = html_render.render_application_html(
        [],
        sections=[
            ApplicationSection(title="Validated applications", applications=[]),
            ApplicationSection(title="Decided applications", applications=[]),
        ],
        search_criteria={"Mode": "Validated and decided in this week"},
    )

    assert "Validated applications" in html
    assert "Decided applications" in html
    assert "Validated and decided in this week" in html
    assert "No applications" in html
