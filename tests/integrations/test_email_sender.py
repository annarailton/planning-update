"""Tests for email sending helpers."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import requests

from planning_update.integrations import email_sender
from planning_update.models import (
    Application,
    ApplicationRef,
    ApplicationSection,
    CommitteeApplication,
    CommitteeSection,
)


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
    assert "Call-in deadline: 2026-03-02 17:00" in text
    assert "View application: https://example.com/app" in text
    assert "Generated 2026-04-13 09:30" in text


def test_build_plain_text_email_includes_keyword_matches(
    application_factory: Callable[..., Application],
) -> None:
    """Plain text email should include matched keywords when present."""
    text = email_sender.build_plain_text_email(
        applications=[application_factory(keyword_matches=["heat pump", "pv"])],
        generated_at=datetime(2026, 4, 13, 9, 30),
        search_criteria={"Keywords": "heat pump, pv"},
    )

    assert "Keyword match: heat pump, pv" in text


def test_build_plain_text_email_includes_application_sections(
    application_factory: Callable[..., Application],
) -> None:
    """Plain text email should render named sections for multi-mode output."""
    text = email_sender.build_plain_text_email(
        applications=[
            application_factory(application_ref={"value": "26/00281/FUL"}),
            application_factory(application_ref={"value": "26/00282/FUL"}),
        ],
        sections=[
            ApplicationSection(
                title="Validated applications",
                applications=[
                    application_factory(application_ref={"value": "26/00281/FUL"})
                ],
            ),
            ApplicationSection(
                title="Decided applications",
                applications=[
                    application_factory(application_ref={"value": "26/00282/FUL"})
                ],
            ),
        ],
        generated_at=datetime(2026, 4, 13, 9, 30),
        search_criteria={"Mode": "Validated and decided in this week"},
    )

    assert "Validated applications" in text
    assert "Decided applications" in text
    assert "26/00281/FUL" in text
    assert "26/00282/FUL" in text


def test_build_plain_text_email_includes_committee_recommendation() -> None:
    """Plain text email should include committee agenda recommendations."""
    text = email_sender.build_plain_text_email(
        applications=[],
        committee_section=CommitteeSection(
            applications=[
                CommitteeApplication(
                    application_ref=ApplicationRef(value="25/03195/FUL"),
                    committee_date="26 May 2026",
                    proposal="Demolition and replacement building.",
                    address="Mansfield College, Mansfield Road, Oxford",
                    agenda_url="https://mycouncil.oxford.gov.uk/agenda",
                    report_url="https://mycouncil.oxford.gov.uk/report.pdf",
                    recommendation="Approve",
                )
            ]
        ),
        generated_at=datetime(2026, 4, 13, 9, 30),
        search_criteria=None,
    )

    assert "Recommendation: Approve" in text
    assert "Agenda: https://mycouncil.oxford.gov.uk/agenda" in text


def test_build_plain_text_email_includes_review_committee_section() -> None:
    """Plain text email should include planning review committee applications."""
    text = email_sender.build_plain_text_email(
        applications=[],
        review_committee_section=CommitteeSection(
            title="Coming to next planning REVIEW committee",
            applications=[
                CommitteeApplication(
                    application_ref=ApplicationRef(value="25/03195/FUL"),
                    committee_date="26 May 2026",
                    proposal="Review committee proposal.",
                    address="Town Hall, Oxford",
                    agenda_url="https://mycouncil.oxford.gov.uk/review-agenda",
                    report_url="https://mycouncil.oxford.gov.uk/review-report.pdf",
                    recommendation="Approve",
                )
            ],
        ),
        generated_at=datetime(2026, 4, 13, 9, 30),
        search_criteria=None,
    )

    assert "Coming to next planning REVIEW committee" in text
    assert "Review committee proposal." in text
    assert "Agenda: https://mycouncil.oxford.gov.uk/review-agenda" in text


def test_build_plain_text_email_includes_empty_committee_message() -> None:
    """Plain text email should show the committee empty state."""
    text = email_sender.build_plain_text_email(
        applications=[],
        committee_section=CommitteeSection(applications=[]),
        generated_at=datetime(2026, 4, 13, 9, 30),
        search_criteria=None,
    )

    assert "Coming to next planning committee" in text
    assert "No upcoming planning committee agenda released." in text


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


def test_build_default_email_log_path_includes_config_basename() -> None:
    """Sent-email log paths should include the config file basename when present."""
    log_path = email_sender.build_default_email_log_path(
        sent_at=datetime(2026, 4, 20, 11, 29, 47, 123456),
        config_path=Path("configs/anna.toml"),
    )

    assert log_path == Path("email_logs/2026-04-20T11-29-47-123456_anna.html")


def test_build_default_email_log_path_without_config() -> None:
    """Sent-email log paths should omit the config slug when no config is used."""
    log_path = email_sender.build_default_email_log_path(
        sent_at=datetime(2026, 4, 20, 11, 29, 47, 123456),
    )

    assert log_path == Path("email_logs/2026-04-20T11-29-47-123456.html")


def test_write_sent_email_log_stores_rendered_html(tmp_path: Path) -> None:
    """Sent-email logs should persist the rendered HTML directly."""
    log_path = tmp_path / "sent-email.html"

    written_path = email_sender.write_sent_email_log(
        html="<p>Hello</p>",
        sent_at=datetime(2026, 4, 20, 11, 29, 47),
        config_path=Path("configs/anna.toml"),
        log_path=log_path,
    )

    assert written_path == log_path
    assert log_path.read_text(encoding="utf-8") == "<p>Hello</p>"


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
