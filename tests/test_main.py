"""Tests for the Typer CLI entry point."""

import re
from collections.abc import Callable
from pathlib import Path

from typer.testing import CliRunner

import main
from models import Application, PlanningQuery

runner = CliRunner()
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def test_cli_writes_html_output_file(
    application_factory: Callable[..., Application],
    monkeypatch,
    tmp_path: Path,
) -> None:
    """CLI should print the application count and write HTML card output to a file."""

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        assert query.ward_name == "churchill"
        assert query.status_mode == "decided"
        assert query.strict is True
        return [application_factory()]

    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )

    output_path = tmp_path / "applications.html"
    result = runner.invoke(
        main.app,
        [
            "--debug",
            "--ward",
            "churchill",
            "--decided",
            "--strict",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "Found 1 applications." in result.stdout
    assert f"Saved HTML output to {output_path}" in result.stdout

    html = output_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "Generated " in html
    assert "Search criteria" in html
    assert "Churchill" in html
    assert "Decided in this week" in html
    assert "Yes" in html
    assert "26/00281/FUL" in html
    assert "Churchill Ward" in html
    assert "Approved" in html
    assert "View application" in html


def test_cli_does_not_write_html_output_without_debug(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should skip writing the HTML file unless debug output is enabled."""

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        return [application_factory()]

    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )

    output_path = tmp_path / "applications.html"
    result = runner.invoke(
        main.app,
        ["--output", str(output_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Found 1 applications." in result.stdout
    assert "Saved HTML output to" not in result.stdout
    assert not output_path.exists()


def test_cli_uses_timestamped_default_output_filename(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should use a timestamped HTML filename when output is not provided."""

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        return [application_factory()]

    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )

    default_output_path = tmp_path / "2026-04-13T09-30-00_planning_applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: default_output_path,
    )

    result = runner.invoke(main.app, ["--debug", "--decided"], catch_exceptions=False)

    assert result.exit_code == 0
    assert f"Saved HTML output to {default_output_path}" in result.stdout
    assert default_output_path.exists()


def test_cli_sends_email_via_resend(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should send the rendered HTML via Resend when requested."""

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        return [application_factory()]

    sent_payload: dict[str, str] = {}

    def fake_send_resend_email(
        *,
        api_key: str,
        recipient: str,
        subject: str,
        html: str,
        text: str,
        sender: str = "anna@railton.dev",
    ) -> str:
        sent_payload.update(
            {
                "api_key": api_key,
                "recipient": recipient,
                "subject": subject,
                "html": html,
                "text": text,
                "sender": sender,
            }
        )
        return "email_123"

    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )
    monkeypatch.setattr(main, "send_resend_email", fake_send_resend_email)
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    output_path = tmp_path / "applications.html"
    result = runner.invoke(
        main.app,
        ["--email-to", "test@example.com", "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert "Sent email to test@example.com via Resend (email_123)." in result.stdout
    assert not output_path.exists()
    assert sent_payload["api_key"] == "re_test_key"
    assert sent_payload["recipient"] == "test@example.com"
    assert sent_payload["sender"] == "anna@railton.dev"
    assert "Oxford planning applications" in sent_payload["subject"]
    assert "<!DOCTYPE html>" in sent_payload["html"]
    assert "Oxford Planning Applications" in sent_payload["text"]


def test_cli_debug_mode_skips_email_and_writes_file(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should write debug HTML and skip sending email when debug is enabled."""

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        return [application_factory()]

    def fail_send_resend_email(**kwargs) -> str:
        raise AssertionError("send_resend_email should not be called in debug mode")

    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )
    monkeypatch.setattr(main, "send_resend_email", fail_send_resend_email)

    output_path = tmp_path / "applications.html"
    result = runner.invoke(
        main.app,
        [
            "--debug",
            "--email-to",
            "test@example.com",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert f"Saved HTML output to {output_path}" in result.stdout
    assert output_path.exists()


def test_cli_rejects_validated_and_decided_together() -> None:
    """CLI should reject selecting both date mode flags."""
    result = runner.invoke(main.app, ["--validated", "--decided"])
    # Typer may emit ANSI styling in CI, so normalize before asserting on text.
    output = ANSI_ESCAPE_RE.sub("", result.output)

    assert result.exit_code != 0
    assert "Use at most one of --validated or --decided." in output


def test_cli_uses_default_config_file(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should load defaults from planning_update.toml in the cwd."""
    config_path = tmp_path / "planning_update.toml"
    config_path.write_text(
        "\n".join(
            [
                'ward = "churchill"',
                'parish = "Littlemore"',
                "debug = true",
                'status_mode = "decided"',
                "fallback_weeks = 3",
                "strict = true",
            ]
        ),
        encoding="utf-8",
    )

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        assert query.ward_name == "churchill"
        assert query.parish_name == "Littlemore"
        assert query.status_mode == "decided"
        assert query.fallback_weeks == 3
        assert query.strict is True
        return [application_factory()]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )
    output_path = tmp_path / "planning_applications.html"
    result = runner.invoke(
        main.app,
        ["--debug", "--output", str(output_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Found 1 applications." in result.stdout
    assert f"Saved HTML output to {output_path}" in result.stdout


def test_cli_arguments_override_config(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI options should override values loaded from config."""
    config_path = tmp_path / "planning_update.toml"
    config_path.write_text(
        "\n".join(
            [
                'ward = "churchill"',
                "debug = true",
                'status_mode = "validated"',
                "fallback_weeks = 4",
                "strict = true",
                'output = "from-config.html"',
                'email_to = "config@example.com"',
            ]
        ),
        encoding="utf-8",
    )

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        assert query.ward_name == "marston"
        assert query.status_mode == "decided"
        assert query.fallback_weeks == 0
        assert query.strict is False
        return [application_factory()]

    sent_payload: dict[str, str] = {}

    def fake_send_resend_email(
        *,
        api_key: str,
        recipient: str,
        subject: str,
        html: str,
        text: str,
        sender: str = "anna@updates.railton.dev",
    ) -> str:
        sent_payload["recipient"] = recipient
        return "email_456"

    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )
    monkeypatch.setattr(main, "send_resend_email", fake_send_resend_email)

    output_path = tmp_path / "from-cli.html"
    result = runner.invoke(
        main.app,
        [
            "--config",
            str(config_path),
            "--no-debug",
            "--ward",
            "marston",
            "--decided",
            "--fallback-weeks",
            "0",
            "--no-strict",
            "--output",
            str(output_path),
            "--email-to",
            "cli@example.com",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Saved HTML output to" not in result.stdout
    assert not output_path.exists()
    assert "Sent email to cli@example.com via Resend (email_456)." in result.stdout
    assert sent_payload["recipient"] == "cli@example.com"
