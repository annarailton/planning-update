"""Tests for email sending helpers."""

from datetime import date, datetime

import email_sender
from models import Application, ApplicationRef


def build_application() -> Application:
    """Build an application fixture for email sender tests."""
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
        consultation_deadline=date(2026, 3, 16),
        determination_deadline=date(2026, 4, 6),
        status="Decided",
        decision="Approved",
    )


def test_build_plain_text_email_includes_core_sections() -> None:
    """Plain text email should include summary, criteria, and application details."""
    text = email_sender.build_plain_text_email(
        applications=[build_application()],
        generated_at=datetime(2026, 4, 13, 9, 30),
        search_criteria={"Ward": "Churchill", "Mode": "Validated in this week"},
    )

    assert "Oxford Planning Applications" in text
    assert "Search criteria:" in text
    assert "- Ward: Churchill" in text
    assert "26/00281/FUL" in text
    assert "View application: https://example.com/app" in text
    assert "Generated 2026-04-13 09:30" in text


def test_build_idempotency_key_is_stable_for_same_payload() -> None:
    """Idempotency key should be stable for the same payload."""
    first = email_sender.build_idempotency_key(
        sender="anna@railton.dev",
        recipient="test@example.com",
        subject="Subject",
        html="<p>Hello</p>",
    )
    second = email_sender.build_idempotency_key(
        sender="anna@railton.dev",
        recipient="test@example.com",
        subject="Subject",
        html="<p>Hello</p>",
    )

    assert first == second
    assert first.startswith("planning-update/")
