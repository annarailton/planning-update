"""Email sending helpers for planning application updates."""

import hashlib
import re
from datetime import datetime
from pathlib import Path

import requests

from ..constants import DEFAULT_SENDER_ADDRESS, RESEND_EMAILS_URL
from ..models import Application, ApplicationSection, CommitteeSection
from ..renderers.html_render import format_generated_timestamp

EMAIL_LOG_DIR = Path("email_logs")


def build_email_subject(
    week: str | None,
) -> str:
    """Build a default email subject for a planning update."""
    week_suffix = f"{week}" if week else "last week"
    return f"Oxford planning applications of interest for {week_suffix}"


def build_plain_text_email(
    *,
    applications: list[Application],
    sections: list[ApplicationSection] | None = None,
    generated_at: datetime,
    search_criteria: dict[str, str] | None,
    committee_section: CommitteeSection | None = None,
) -> str:
    """Build a plain-text fallback version of the planning update email."""
    lines = [
        "Oxford Planning Applications",
        "",
        f"Found {len(applications)} application{'s' if len(applications) != 1 else ''} of interest.",
    ]

    if search_criteria:
        lines.extend(["", "Search criteria:"])
        lines.extend(f"- {label}: {value}" for label, value in search_criteria.items())

    def append_application_details(section_applications: list[Application]) -> None:
        for application in section_applications:
            details = [
                "",
                application.application_ref.value,
                application.proposal,
                application.address,
                f"Ward: {application.ward or 'Not provided'}",
                f"Received: {application.received.isoformat()}",
                f"Validated: {application.validated.isoformat()}",
            ]
            if application.keyword_matches:
                details.append(
                    f"Keyword match: {', '.join(application.keyword_matches)}"
                )
            details.extend(
                [
                    f"Status: {application.status or 'N/A'}",
                    (
                        "Consultation deadline: "
                        f"{application.consultation_deadline.isoformat() if application.consultation_deadline else 'N/A'}"
                    ),
                    (
                        "Determination deadline: "
                        f"{application.determination_deadline.isoformat() if application.determination_deadline else 'N/A'}"
                    ),
                    f"Decision: {application.decision or 'N/A'}",
                    (
                        "Decided: "
                        f"{application.decided.isoformat() if application.decided else 'N/A'}"
                    ),
                    f"View application: {application.url}",
                ]
            )
            lines.extend(details)

    if sections:
        for section in sections:
            lines.extend(["", section.title])
            if section.applications:
                append_application_details(section.applications)
            else:
                lines.append(section.empty_state_message)
    else:
        append_application_details(applications)

    if committee_section and committee_section.applications:
        lines.extend(["", committee_section.title])
        for application in committee_section.applications:
            details = [
                "",
                application.application_ref.value,
                application.proposal,
                f"Committee date: {application.committee_date.isoformat()}",
            ]
            if application.recommendation:
                details.append(f"Recommendation: {application.recommendation}")
            details.extend(
                [
                    f"Agenda: {application.agenda_url}",
                    f"View committee report: {application.report_url}",
                ]
            )
            lines.extend(details)

    lines.extend(["", f"Generated {format_generated_timestamp(generated_at)}"])
    return "\n".join(lines)


def build_idempotency_key(
    *,
    sender: str,
    recipient: str,
    subject: str,
    html: str,
) -> str:
    """Build a stable idempotency key for a given email payload."""
    digest = hashlib.sha256(
        f"{sender}\n{recipient}\n{subject}\n{html}".encode("utf-8")
    ).hexdigest()
    return f"planning-update/{digest[:40]}"


def safe_filename_part(value: str) -> str:
    """Return a filesystem-friendly label for generated log filenames."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return slug or "config"


def build_default_email_log_path(
    *, sent_at: datetime, config_path: Path | None = None
) -> Path:
    """Build the default timestamped sent-email log path."""
    timestamp_slug = sent_at.strftime("%Y-%m-%dT%H-%M-%S-%f")
    config_slug = ""
    if config_path is not None:
        config_slug = f"_{safe_filename_part(config_path.stem)}"
    return EMAIL_LOG_DIR.joinpath(f"{timestamp_slug}{config_slug}.html")


def write_sent_email_log(
    *,
    html: str,
    sent_at: datetime,
    config_path: Path | None = None,
    log_path: Path | None = None,
) -> Path:
    """Write the rendered HTML for a successfully sent email."""
    resolved_log_path = log_path or build_default_email_log_path(
        sent_at=sent_at,
        config_path=config_path,
    )
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_log_path.write_text(html, encoding="utf-8")
    return resolved_log_path


def send_resend_email(
    *,
    api_key: str,
    recipient: str,
    subject: str,
    html: str,
    text: str | None = None,
    sender: str = DEFAULT_SENDER_ADDRESS,
) -> str:
    """Send an email through Resend and return the message id."""
    payload = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "html": html,
    }
    if text is not None:
        payload["text"] = text

    response = requests.post(
        RESEND_EMAILS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": build_idempotency_key(
                sender=sender,
                recipient=recipient,
                subject=subject,
                html=html,
            ),
        },
        json=payload,
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text.strip()
        if response.status_code == 403:
            raise ValueError(
                "Resend rejected the send request with 403 Forbidden. "
                f"This often means the sender domain is not verified for the from address '{sender}'. "
                f"Response: {detail}"
            ) from exc
        raise ValueError(
            f"Resend request failed with status {response.status_code}. Response: {detail}"
        ) from exc
    payload = response.json()
    email_id = payload.get("id")
    if not email_id:
        raise ValueError("Resend response did not include an email id")
    return str(email_id)
