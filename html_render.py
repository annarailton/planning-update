"""HTML rendering for planning application results."""

from datetime import date, datetime
from html import escape

from constants import (
    ACCENT_WARM_COLOR,
    BORDER_SUBTLE_COLOR,
    DANGER_COLOR,
    LINK_COLOR,
    PAGE_BACKGROUND_COLOR,
    SHADOW_COLOR,
    SUCCESS_COLOR,
    SURFACE_PRIMARY_COLOR,
    SURFACE_SECONDARY_COLOR,
    TEXT_PRIMARY_COLOR,
    TEXT_SECONDARY_COLOR,
    TEXT_STRONG_COLOR,
    TEXT_TERTIARY_COLOR,
    WARNING_COLOR,
)
from models import Application, PlanningQuery


def current_date() -> date:
    """Return the current local date for rendering comparisons.

    Exists so can be mocked in tests.
    """
    return date.today()


def current_datetime() -> datetime:
    """Return the current local datetime for rendering timestamps.

    Exists so can be mocked in tests.
    """
    return datetime.now()


def format_application_date(value: date | None) -> str:
    """Render application date values consistently for HTML output."""
    if value is None:
        return "Not provided"
    return escape(value.strftime("%Y-%m-%d"))


def format_generated_timestamp(value: datetime) -> str:
    """Render the generated-at timestamp for the HTML output."""
    return escape(value.strftime("%Y-%m-%d %H:%M"))


def date_css_class(value: date | None, *, today: date) -> str:
    """Return a modifier CSS class for a date relative to today."""
    if value is None:
        return ""
    if value >= today:
        return " field-value--date-future"
    return " field-value--date-past"


def decision_css_class(decision: str | None) -> str:
    """Return a modifier CSS class for known decision values."""
    if decision in {"Approved", "Prior approval not required"}:
        return " field-value--decision-approved"
    if decision == "Rejected":
        return " field-value--decision-rejected"
    return ""


def status_css_class(status: str | None) -> str:
    """Return a modifier CSS class for known status values."""
    if status == "Decided":
        return " field-value--status-decided"
    if status == "Registered":
        return " field-value--status-registered"
    return ""


def decision_date_css_class(value: date | None, *, today: date) -> str:
    """Return a modifier CSS class for a past decision date."""
    if value is None:
        return ""
    if value < today:
        return " field-value--decision-date-past"
    return ""


def build_search_criteria(
    *,
    query: PlanningQuery,
    validated: bool,
    decided: bool,
) -> dict[str, str]:
    """Build the rendered search criteria summary for the HTML output."""
    mode = "Decided in this week" if decided else "Validated in this week"
    if validated:
        mode = "Validated in this week"

    return {
        "Ward": query.resolved_ward_name(),
        "Parish": query.resolved_parish_name(),
        "Mode": mode,
        "Week": query.requested_week or "Latest available",
        "Fallback weeks": str(query.fallback_weeks),
        "Strict mode": "Yes" if query.strict else "No",
    }


def render_application_html(
    applications: list[Application],
    *,
    search_criteria: dict[str, str] | None = None,
    today: date | None = None,
) -> str:
    """Render applications as a simple HTML document with one card per application."""
    render_today = today or current_date()
    rendered_at = current_datetime()

    def render_field(label: str, value: str, value_class: str = "") -> str:
        return (
            '<div class="field">'
            f'<div class="field-label">{escape(label)}</div>'
            f'<div class="field-value{value_class}">{value}</div>'
            "</div>"
        )

    cards: list[str] = []
    for application in applications:
        cards.append(
            (
                '<article class="card">'
                f'<div class="eyebrow">{escape(application.application_ref.value)}</div>'
                f"<h2>{escape(application.proposal)}</h2>"
                f'<p class="address">{escape(application.address)}</p>'
                f'<p><a href="{escape(application.url, quote=True)}">View application</a></p>'
                '<div class="fields">'
                f"{render_field('Ward', escape(application.ward or 'Not provided'))}"
                f"{render_field('Received', format_application_date(application.received))}"
                f"{render_field('Validated', format_application_date(application.validated))}"
                f"{render_field('Status', escape(application.status or 'Not provided'), status_css_class(application.status))}"
                f"{render_field('Consultation deadline', format_application_date(application.consultation_deadline), date_css_class(application.consultation_deadline, today=render_today))}"
                f"{render_field('Determination deadline', format_application_date(application.determination_deadline), date_css_class(application.determination_deadline, today=render_today))}"
                f"{render_field('Decision', escape(application.decision or 'Not provided'), decision_css_class(application.decision))}"
                f"{render_field('Decision date', format_application_date(application.decided), decision_date_css_class(application.decided, today=render_today))}"
                "</div>"
                "</article>"
            )
        )

    criteria_fields = ""
    if search_criteria:
        criteria_fields = "".join(
            (
                '<span class="criteria-item">'
                f'<span class="criteria-label">{escape(label)}:</span> '
                f'<span class="criteria-value">{escape(value)}</span>'
                "</span>"
            )
            for label, value in search_criteria.items()
        )

    return (
        "<!DOCTYPE html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Oxford Planning Applications</title>"
        "<style>"
        ":root{"
        f"--color-page-background:{PAGE_BACKGROUND_COLOR};"
        f"--color-text-primary:{TEXT_PRIMARY_COLOR};"
        f"--color-text-secondary:{TEXT_SECONDARY_COLOR};"
        f"--color-text-tertiary:{TEXT_TERTIARY_COLOR};"
        f"--color-text-strong:{TEXT_STRONG_COLOR};"
        f"--color-surface-primary:{SURFACE_PRIMARY_COLOR};"
        f"--color-surface-secondary:{SURFACE_SECONDARY_COLOR};"
        f"--color-border-subtle:{BORDER_SUBTLE_COLOR};"
        f"--color-accent-warm:{ACCENT_WARM_COLOR};"
        f"--color-link:{LINK_COLOR};"
        f"--color-shadow:{SHADOW_COLOR};"
        f"--color-success:{SUCCESS_COLOR};"
        f"--color-warning:{WARNING_COLOR};"
        f"--color-danger:{DANGER_COLOR};"
        "}"
        "body{margin:0;padding:24px;background:var(--color-page-background);color:var(--color-text-primary);"
        "font-family:Arial,sans-serif;line-height:1.5;}"
        ".wrapper{max-width:960px;margin:0 auto;}"
        "h1{margin:0 0 8px;font-size:32px;line-height:1.1;}"
        ".timestamp{margin:0 0 8px;color:var(--color-text-secondary);font-size:13px;}"
        ".summary{margin:0 0 16px;color:var(--color-text-secondary);}"
        ".criteria{margin:0 0 20px;padding:12px 16px;background:var(--color-surface-primary);border:1px solid var(--color-border-subtle);"
        "border-radius:12px;box-shadow:0 4px 12px var(--color-shadow);}"
        ".criteria h2{margin:0 0 8px;font-size:15px;line-height:1.2;}"
        ".criteria-list{display:flex;flex-wrap:wrap;gap:8px 14px;font-size:13px;line-height:1.4;}"
        ".criteria-item{color:var(--color-text-secondary);}"
        ".criteria-label{font-weight:700;color:var(--color-text-strong);}"
        ".cards{display:grid;gap:16px;}"
        ".card{background:var(--color-surface-primary);border:1px solid var(--color-border-subtle);border-radius:12px;"
        "padding:20px;box-shadow:0 4px 12px var(--color-shadow);}"
        ".eyebrow{font-size:12px;font-weight:700;letter-spacing:0.08em;"
        "text-transform:uppercase;color:var(--color-accent-warm);margin-bottom:10px;}"
        ".card h2{margin:0 0 8px;font-size:24px;line-height:1.2;}"
        ".address{margin:0 0 12px;color:var(--color-text-secondary);}"
        ".fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;}"
        ".field{padding:12px;background:var(--color-surface-secondary);border-radius:8px;}"
        ".field-label{font-size:12px;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.05em;color:var(--color-text-tertiary);margin-bottom:4px;}"
        ".field-value{font-size:14px;word-break:break-word;}"
        ".field-value--date-future{color:var(--color-success);font-weight:700;}"
        ".field-value--date-past{color:var(--color-danger);font-weight:700;}"
        ".field-value--decision-approved{color:var(--color-success);font-weight:700;}"
        ".field-value--decision-rejected{color:var(--color-danger);font-weight:700;}"
        ".field-value--status-decided{color:var(--color-success);font-weight:700;}"
        ".field-value--status-registered{color:var(--color-warning);font-weight:700;}"
        ".field-value--decision-date-past{color:var(--color-success);font-weight:700;}"
        "a{color:var(--color-link);text-decoration:none;}"
        "a:hover{text-decoration:underline;}"
        "</style>"
        "</head>"
        "<body>"
        '<main class="wrapper">'
        "<h1>Oxford Planning Applications</h1>"
        f'<p class="timestamp">Generated {format_generated_timestamp(rendered_at)}</p>'
        f'<p class="summary">Found {len(applications)} application{"s" if len(applications) != 1 else ""}.</p>'
        f'<section class="criteria"><h2>Search criteria</h2><div class="criteria-list">{criteria_fields}</div></section>'
        f'<section class="cards">{"".join(cards)}</section>'
        "</main>"
        "</body>"
        "</html>"
    )
