"""HTML rendering for planning application results."""

from datetime import date, datetime
from html import escape

from ..constants import (
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
from ..models import Application, ApplicationSection, ResolvedCliOptions


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
        return "N/A"
    return escape(value.strftime("%Y-%m-%d"))


def format_optional_text(value: str | None) -> str:
    """Render optional string values consistently for HTML output."""
    return escape(value or "N/A")


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
    if decision in {"Rejected", "Application Withdrawn"}:
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


def keyword_match_css_class(keyword_matches: list[str] | None) -> str:
    """Return a modifier CSS class when keyword matches are present."""
    if keyword_matches:
        return " field-value--keyword-match"
    return ""


def major_application_css_class(is_major_application: bool) -> str:
    """Return a modifier CSS class when an application is on the major list."""
    if is_major_application:
        return " field-value--major-application"
    return ""


def build_search_criteria(
    *,
    options: ResolvedCliOptions,
) -> dict[str, str]:
    """Build the rendered search criteria summary for the HTML output."""
    queries = options.queries
    primary_query = next(
        (
            query
            for query in queries
            if not query.uses_keyword_matching() and not query.uses_major_matching()
        ),
        queries[0],
    )
    keywords = next((query.keywords for query in queries if query.keywords), [])
    includes_major = any(query.major for query in queries)

    mode = {
        "validated": "Validated in this week",
        "decided": "Decided in this week",
        "both": "Validated and decided in this week",
    }[options.status_mode]

    return {
        "Ward": primary_query.resolved_ward_name(),
        "Parish": primary_query.resolved_parish_name(),
        **({"Keywords": ", ".join(keywords)} if keywords else {}),
        **({"Major applications": "Yes"} if includes_major else {}),
        "Mode": mode,
        "Week": primary_query.requested_week or "Latest available",
    }


def render_application_html(
    applications: list[Application],
    *,
    sections: list[ApplicationSection] | None = None,
    search_criteria: dict[str, str] | None = None,
    today: date | None = None,
) -> str:
    """Render applications as a simple email-friendly HTML document."""
    render_today = today or current_date()
    rendered_at = current_datetime()

    def render_fields_table(
        fields: list[tuple[str, str, str]],
    ) -> str:
        rows: list[str] = []
        for index in range(0, len(fields), 2):
            left_label, left_value, left_class = fields[index]
            if index + 1 < len(fields):
                right_label, right_value, right_class = fields[index + 1]
            else:
                right_label, right_value, right_class = "", "", ""

            rows.append(
                (
                    '<tr class="field-row">'
                    f'<td class="field-label" valign="top">{escape(left_label)}</td>'
                    f'<td class="field-value{left_class}" valign="top">{left_value}</td>'
                    f'<td class="field-label" valign="top">{escape(right_label)}</td>'
                    f'<td class="field-value{right_class}" valign="top">{right_value}</td>'
                    "</tr>"
                )
            )
        return "".join(rows)

    def render_cards(
        items: list[Application], *, empty_state_message: str = "No applications"
    ) -> str:
        if not items:
            return (
                '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="card card--empty">'
                f'<tr><td><p class="empty-state">{escape(empty_state_message)}</p></td></tr>'
                "</table>"
            )

        cards: list[str] = []
        for application in items:
            fields = [
                ("Ward", escape(application.ward or "Not provided"), ""),
                (
                    "Status",
                    format_optional_text(application.status),
                    status_css_class(application.status),
                ),
                ("Received", format_application_date(application.received), ""),
                ("Validated", format_application_date(application.validated), ""),
                (
                    "Consultation deadline",
                    format_application_date(application.consultation_deadline),
                    date_css_class(
                        application.consultation_deadline, today=render_today
                    ),
                ),
                (
                    "Determination deadline",
                    format_application_date(application.determination_deadline),
                    date_css_class(
                        application.determination_deadline, today=render_today
                    ),
                ),
                (
                    "Decision",
                    format_optional_text(application.decision),
                    decision_css_class(application.decision),
                ),
                (
                    "Decided",
                    format_application_date(application.decided),
                    decision_date_css_class(application.decided, today=render_today),
                ),
                (
                    (
                        "Keyword match",
                        escape(", ".join(application.keyword_matches or [])),
                        keyword_match_css_class(application.keyword_matches),
                    )
                    if application.keyword_matches
                    else None
                ),
                (
                    (
                        "Major application",
                        "Yes",
                        major_application_css_class(application.is_major_application),
                    )
                    if application.is_major_application
                    else None
                ),
            ]
            fields = [field for field in fields if field is not None]
            cards.append(
                (
                    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="card">'
                    "<tr><td>"
                    f'<div class="eyebrow">{escape(application.application_ref.value)}</div>'
                    f'<h2 class="card-title">{escape(application.proposal)}</h2>'
                    f'<p class="address">{escape(application.address)}</p>'
                    f'<p class="link-row"><a href="{escape(application.url, quote=True)}">View application</a></p>'
                    '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="fields">'
                    f"{render_fields_table(fields)}"
                    "</table>"
                    "</td></tr>"
                    "</table>"
                )
            )
        return "".join(cards)

    rendered_sections = ""
    if sections:
        rendered_sections = "".join(
            (
                f'<h2 class="section-title">{escape(section.title)}</h2>'
                + (
                    f'<p class="section-notice">{escape(section.major_apps_notice_message)}</p>'
                    if section.major_apps_notice_message
                    else ""
                )
                + (
                    f"{render_cards(section.applications, empty_state_message=section.empty_state_message)}"
                )
            )
            for section in sections
        )
    else:
        rendered_sections = render_cards(applications)

    criteria_fields = ""
    if search_criteria:
        criteria_fields = "".join(
            (
                '<tr class="criteria-item">'
                f'<td class="criteria-label" valign="top">{escape(label)}:</td>'
                f'<td class="criteria-value" valign="top">{escape(value)}</td>'
                "</tr>"
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
        "body{margin:0;padding:0;background:var(--color-page-background);color:var(--color-text-primary);font-family:Arial,sans-serif;line-height:1.5;}"
        "table{border-collapse:collapse;mso-table-lspace:0pt;mso-table-rspace:0pt;}"
        ".email-shell{background:var(--color-page-background);}"
        ".wrapper{width:100%;max-width:960px;margin:0 auto;}"
        ".content-cell{padding:24px;}"
        "h1{margin:0 0 8px;font-size:32px;line-height:1.1;}"
        ".timestamp{margin:16px 0 8px;color:var(--color-text-secondary);font-size:13px;}"
        ".summary{margin:0 0 16px;color:var(--color-text-secondary);}"
        ".criteria{background:var(--color-surface-primary);border:1px solid var(--color-border-subtle);border-radius:12px;box-shadow:0 4px 12px var(--color-shadow);}"
        ".criteria-cell{padding:10px 14px;}"
        ".criteria h2{margin:0 0 8px;font-size:15px;line-height:1.2;}"
        ".criteria-list{width:100%;font-size:13px;line-height:1.4;}"
        ".criteria-item{color:var(--color-text-secondary);}"
        ".criteria-label{font-weight:700;color:var(--color-text-strong);padding:0 10px 6px 0;white-space:nowrap;}"
        ".criteria-value{color:var(--color-text-secondary);padding:0 0 6px 0;}"
        ".section-title{margin:18px 0 8px;font-size:18px;line-height:1.2;color:var(--color-text-strong);}"
        ".section-notice{margin:0 0 8px;color:var(--color-text-secondary);font-size:14px;font-weight:700;}"
        ".card{background:var(--color-surface-primary);border:1px solid var(--color-border-subtle);border-radius:12px;box-shadow:0 4px 12px var(--color-shadow);margin-top:12px;}"
        ".card td{padding:14px;}"
        ".card--empty td{padding:18px 14px;}"
        ".empty-state{margin:0;font-size:16px;font-weight:700;color:var(--color-text-secondary);}"
        ".eyebrow{font-size:12px;font-weight:700;letter-spacing:0.08em;"
        "text-transform:uppercase;color:var(--color-accent-warm);margin-bottom:10px;}"
        ".card-title{margin:0 0 8px;font-size:24px;line-height:1.2;}"
        ".address{margin:0 0 8px;color:var(--color-text-secondary);}"
        ".link-row{margin:0 0 8px;}"
        ".link-row a{display:inline-block;font-size:15px;font-weight:700;padding-left:2px;}"
        ".fields{width:100%;}"
        ".field-row{background:var(--color-surface-secondary);}"
        ".field-row + .field-row td{border-top:6px solid var(--color-surface-primary);}"
        ".field-label{font-size:12px;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.05em;color:var(--color-text-tertiary);padding:9px 8px 9px 12px;width:120px;}"
        ".field-value{font-size:14px;word-break:break-word;padding:9px 12px 9px 10px;}"
        ".field-value--date-future{color:var(--color-success);font-weight:700;}"
        ".field-value--date-past{color:var(--color-danger);font-weight:700;}"
        ".field-value--decision-approved{color:var(--color-success);font-weight:700;}"
        ".field-value--decision-rejected{color:var(--color-danger);font-weight:700;}"
        ".field-value--status-decided{color:var(--color-success);font-weight:700;}"
        ".field-value--status-registered{color:var(--color-warning);font-weight:700;}"
        ".field-value--decision-date-past{color:var(--color-success);font-weight:700;}"
        ".field-value--keyword-match{color:var(--color-success);font-weight:700;}"
        ".field-value--major-application{color:var(--color-success);font-weight:700;}"
        "a{color:var(--color-link);text-decoration:none;}"
        "a:hover{text-decoration:underline;}"
        "</style>"
        "</head>"
        "<body>"
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="email-shell">'
        '<tr><td align="center">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="wrapper">'
        '<tr><td class="content-cell">'
        "<h1>Oxford Planning Applications</h1>"
        f'<p class="summary">Found {len(applications)} application{"s" if len(applications) != 1 else ""}.</p>'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="criteria"><tr><td class="criteria-cell">'
        "<h2>Search criteria</h2>"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="criteria-list">{criteria_fields}</table>'
        "</td></tr></table>"
        f"{rendered_sections}"
        f'<p class="timestamp">Generated {format_generated_timestamp(rendered_at)}</p>'
        "</td></tr></table>"
        "</td></tr></table>"
        "</body>"
        "</html>"
    )
