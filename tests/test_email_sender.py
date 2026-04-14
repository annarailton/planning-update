"""Tests for email sending helpers."""

from collections.abc import Callable
from datetime import datetime

import requests

import email_sender
from models import Application


def test_build_plain_text_email_includes_core_sections(
    application_factory: Callable[..., Application],
) -> None:
    """Plain text email should include summary, criteria, and application details."""
    text = email_sender.build_plain_text_email(
        applications=[application_factory()],
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


def test_send_resend_email_raises_helpful_403_error(monkeypatch) -> None:
    """403 errors from Resend should mention sender domain verification."""

    class FakeResponse:
        status_code = 403
        text = '{"message":"You can only send from verified domains"}'

        def raise_for_status(self) -> None:
            raise requests.HTTPError("403 Client Error", response=self)

    monkeypatch.setattr(
        email_sender.requests, "post", lambda *args, **kwargs: FakeResponse()
    )

    try:
        email_sender.send_resend_email(
            api_key="re_test_key",
            recipient="test@example.com",
            subject="Subject",
            html="<p>Hello</p>",
            text="Hello",
            sender="anna@railton.dev",
        )
    except ValueError as exc:
        assert "sender domain is not verified" in str(exc)
        assert "anna@railton.dev" in str(exc)
    else:
        raise AssertionError("Expected ValueError for 403 response")
