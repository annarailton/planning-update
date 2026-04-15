"""Tests for the Typer CLI entry point."""

from collections.abc import Callable
import os
from pathlib import Path

from typer.testing import CliRunner

from planning_update import cli as main
from planning_update.models import (
    Application,
    ApplicationSection,
    PlanningQuery,
    PlanningReport,
)

runner = CliRunner()


def build_report_from_applications(
    applications: list[Application],
    *,
    status_mode: str = "both",
) -> PlanningReport:
    """Build a minimal PlanningReport for CLI tests."""
    validated_applications = (
        applications if status_mode in {"validated", "both"} else []
    )
    decided_applications = applications if status_mode == "both" else []
    if status_mode == "decided":
        decided_applications = applications

    return PlanningReport(
        applications=validated_applications + decided_applications,
        sections=[
            ApplicationSection(
                title="Validated applications",
                applications=validated_applications,
                empty_state_message=(
                    "No applications"
                    if status_mode in {"validated", "both"}
                    else "Not searched"
                ),
            ),
            ApplicationSection(
                title="Decided applications",
                applications=decided_applications,
                empty_state_message=(
                    "No applications"
                    if status_mode in {"decided", "both"}
                    else "Not searched"
                ),
            ),
        ],
    )


def test_cli_writes_html_output_file(
    application_factory: Callable[..., Application],
    monkeypatch,
    tmp_path: Path,
) -> None:
    """CLI should print the application count and write HTML card output to a file."""

    def fake_build_planning_report(*, options) -> PlanningReport:
        assert options.queries[0].ward_name == "churchill"
        assert options.queries[0].status_mode == "decided"
        return build_report_from_applications(
            [application_factory()],
            status_mode="decided",
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    output_path = tmp_path / "applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        [
            "--debug",
            "--ward",
            "churchill",
            "--status",
            "decided",
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
    assert "Validated applications" in html
    assert "Not searched" in html
    assert "26/00281/FUL" in html
    assert "Churchill Ward" in html
    assert "Approved" in html
    assert "View application" in html


def test_cli_keywords_are_passed_to_query_and_rendered(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should pass comma-delimited keywords into the query and HTML output."""
    seen_queries: list[tuple[str, list[str]]] = []

    def fake_build_planning_report(*, options) -> PlanningReport:
        seen_queries.extend(
            (query.status_mode, query.keywords) for query in options.queries
        )
        application = application_factory(
            keyword_matches=["ashp", "pv"],
            application_ref={"value": "26/00281/FUL"},
        )
        return PlanningReport(
            applications=[application, application],
            sections=[
                ApplicationSection(
                    title="Validated applications",
                    applications=[application],
                ),
                ApplicationSection(
                    title="Decided applications",
                    applications=[application],
                ),
            ],
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    output_path = tmp_path / "applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        [
            "--debug",
            "--keywords",
            "photovoltaics, heat pump, ASHP, PV",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert seen_queries == [
        ("validated", ["photovoltaics", "heat pump", "ashp", "pv"]),
        ("decided", ["photovoltaics", "heat pump", "ashp", "pv"]),
    ]
    html = output_path.read_text(encoding="utf-8")
    assert "Keywords" in html
    assert "photovoltaics, heat pump, ashp, pv" in html
    assert "Validated applications" in html
    assert "Decided applications" in html
    assert "Keyword match" in html
    assert "ashp, pv" in html


def test_cli_multiple_wards_expand_into_multiple_queries(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """Repeated --ward flags should create one location query per ward."""
    seen_wards: list[tuple[str | None, str]] = []

    def fake_build_planning_report(*, options) -> PlanningReport:
        seen_wards.extend(
            (query.ward_name, query.status_mode) for query in options.queries
        )
        return build_report_from_applications(
            [application_factory()],
            status_mode="validated",
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    output_path = tmp_path / "applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        [
            "--debug",
            "--status",
            "validated",
            "--ward",
            "churchill",
            "--ward",
            "hinksey park",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert seen_wards == [
        ("churchill", "validated"),
        ("hinksey park", "validated"),
    ]
    html = output_path.read_text(encoding="utf-8")
    assert "Wards" in html
    assert "Churchill Ward, Hinksey Park" in html


def test_cli_does_not_write_html_output_without_debug(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should skip writing the HTML file unless debug output is enabled."""

    def fake_build_planning_report(*, options) -> PlanningReport:
        return build_report_from_applications(
            [application_factory()], status_mode="both"
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    output_path = tmp_path / "applications.html"
    result = runner.invoke(
        main.app,
        ["--status", "both"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Found 2 applications." in result.stdout
    assert "Saved HTML output to" not in result.stdout
    assert not output_path.exists()


def test_cli_debug_writes_html_output_when_no_applications(
    monkeypatch, tmp_path: Path
) -> None:
    """CLI should still write an empty-state HTML file in debug mode."""

    def fake_build_planning_report(*, options) -> PlanningReport:
        return build_report_from_applications([], status_mode="both")

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    output_path = tmp_path / "applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        ["--debug"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Found 0 applications." in result.stdout
    assert f"Saved HTML output to {output_path}" in result.stdout
    html = output_path.read_text(encoding="utf-8")
    assert "Validated applications" in html
    assert "Decided applications" in html
    assert "No applications" in html
    assert "Not searched" not in html


def test_cli_uses_timestamped_default_output_filename(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should use a timestamped HTML filename when output is not provided."""

    def fake_build_planning_report(*, options) -> PlanningReport:
        return build_report_from_applications(
            [application_factory()],
            status_mode="decided",
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    default_output_path = tmp_path / "2026-04-13T09-30-00_planning_applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: default_output_path,
    )

    result = runner.invoke(
        main.app,
        ["--debug", "--status", "decided"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert f"Saved HTML output to {default_output_path}" in result.stdout
    assert default_output_path.exists()


def test_cli_sends_email_via_resend(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should send the rendered HTML via Resend when requested."""

    def fake_build_planning_report(*, options) -> PlanningReport:
        return build_report_from_applications(
            [application_factory()], status_mode="both"
        )

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

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)
    monkeypatch.setattr(main, "send_resend_email", fake_send_resend_email)
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")

    output_path = tmp_path / "applications.html"
    result = runner.invoke(
        main.app,
        ["--email-to", "test@example.com"],
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


def test_cli_email_fails_before_scraping_when_resend_key_missing(
    monkeypatch,
) -> None:
    """CLI should fail before building the report if email is requested without a key."""

    def fail_build_planning_report(*, options) -> PlanningReport:
        raise AssertionError("build_planning_report should not be called")

    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setattr(main, "build_planning_report", fail_build_planning_report)
    monkeypatch.setattr(main, "load_dotenv", lambda: None)

    result = runner.invoke(
        main.app,
        ["--email-to", "test@example.com"],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    assert "RESEND_API_KEY must be set when using --email-to." in result.stderr


def test_cli_email_loads_resend_key_from_dotenv(
    application_factory: Callable[..., Application], monkeypatch
) -> None:
    """CLI should load a Resend API key from .env before sending email."""

    def fake_build_planning_report(*, options) -> PlanningReport:
        return build_report_from_applications(
            [application_factory()], status_mode="both"
        )

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
        sent_payload["api_key"] = api_key
        sent_payload["recipient"] = recipient
        return "email_dotenv"

    def fake_load_dotenv() -> None:
        os.environ["RESEND_API_KEY"] = "re_dotenv_key"

    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)
    monkeypatch.setattr(main, "send_resend_email", fake_send_resend_email)
    monkeypatch.setattr(main, "load_dotenv", fake_load_dotenv)

    result = runner.invoke(
        main.app,
        ["--email-to", "test@example.com"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Sent email to test@example.com via Resend (email_dotenv)." in result.stdout
    assert sent_payload == {
        "api_key": "re_dotenv_key",
        "recipient": "test@example.com",
    }


def test_cli_debug_mode_skips_email_and_writes_file(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should write debug HTML and skip sending email when debug is enabled."""

    def fake_build_planning_report(*, options) -> PlanningReport:
        return build_report_from_applications(
            [application_factory()], status_mode="both"
        )

    def fail_send_resend_email(**kwargs) -> str:
        raise AssertionError("send_resend_email should not be called in debug mode")

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)
    monkeypatch.setattr(main, "send_resend_email", fail_send_resend_email)

    output_path = tmp_path / "applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        [
            "--debug",
            "--email-to",
            "test@example.com",
        ],
    )

    assert result.exit_code == 0
    assert f"Saved HTML output to {output_path}" in result.stdout
    assert output_path.exists()


def test_cli_both_status_renders_two_sections(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should fetch validated then decided results and render both sections."""
    seen_modes: list[str] = []

    def fake_build_planning_report(*, options) -> PlanningReport:
        seen_modes.extend(query.status_mode for query in options.queries)
        validated = [application_factory(application_ref={"value": "26/00281/FUL"})]
        decided = [application_factory(application_ref={"value": "26/00282/FUL"})]
        return PlanningReport(
            applications=validated + decided,
            sections=[
                ApplicationSection(
                    title="Validated applications", applications=validated
                ),
                ApplicationSection(title="Decided applications", applications=decided),
            ],
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    output_path = tmp_path / "applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        ["--debug", "--status", "both"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert seen_modes == ["validated", "decided"]
    html = output_path.read_text(encoding="utf-8")
    assert "Validated applications" in html
    assert "Decided applications" in html
    assert "Validated and decided in this week" in html


def test_cli_single_status_marks_other_section_not_searched(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """Single-status runs should still render both sections with a skipped marker."""
    seen_modes: list[str] = []

    def fake_build_planning_report(*, options) -> PlanningReport:
        seen_modes.extend(query.status_mode for query in options.queries)
        return build_report_from_applications(
            [application_factory(application_ref={"value": "26/00281/FUL"})],
            status_mode="validated",
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    output_path = tmp_path / "applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        ["--debug", "--status", "validated"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert seen_modes == ["validated"]
    html = output_path.read_text(encoding="utf-8")
    assert "Validated applications" in html
    assert "Decided applications" in html
    assert "No applications" not in html
    assert "Not searched" in html


def test_cli_both_status_renders_two_empty_sections(
    monkeypatch, tmp_path: Path
) -> None:
    """CLI should still render both sections in both-mode when both are empty."""
    seen_modes: list[str] = []

    def fake_build_planning_report(*, options) -> PlanningReport:
        seen_modes.extend(query.status_mode for query in options.queries)
        return build_report_from_applications([], status_mode="both")

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)

    output_path = tmp_path / "applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        ["--debug", "--status", "both"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert seen_modes == ["validated", "decided"]
    assert "Found 0 applications." in result.stdout
    html = output_path.read_text(encoding="utf-8")
    assert "Validated applications" in html
    assert "Decided applications" in html
    assert html.count("No applications") == 2


def test_cli_uses_explicit_config_file(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should load defaults from an explicitly provided config file."""
    config_path = tmp_path / "planning_update.toml"
    config_path.write_text(
        "\n".join(
            [
                'ward = "churchill"',
                'parish = "Littlemore"',
                "debug = true",
                'status_mode = "decided"',
                "major = true",
            ]
        ),
        encoding="utf-8",
    )

    def fake_build_planning_report(*, options) -> PlanningReport:
        assert len(options.queries) == 1
        query = options.queries[0]
        assert query.ward_name == "churchill"
        assert query.parish_name == "Littlemore"
        assert query.status_mode == "decided"
        assert query.major is False
        return build_report_from_applications(
            [application_factory()],
            status_mode="decided",
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)
    output_path = tmp_path / "planning_applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        ["--config", str(config_path), "--debug"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Found 1 applications." in result.stdout
    assert f"Saved HTML output to {output_path}" in result.stdout


def test_cli_reads_multiple_wards_from_config(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI should expand multiple wards from config lists into separate queries."""
    config_path = tmp_path / "planning_update.toml"
    config_path.write_text(
        "\n".join(
            [
                'ward = ["churchill", "hinksey park"]',
                "debug = true",
                'status_mode = "validated"',
            ]
        ),
        encoding="utf-8",
    )

    def fake_build_planning_report(*, options) -> PlanningReport:
        assert options.queries == [
            PlanningQuery(
                ward_name="churchill",
                status_mode="validated",
            ),
            PlanningQuery(
                ward_name="hinksey park",
                status_mode="validated",
            ),
        ]
        return build_report_from_applications(
            [application_factory()],
            status_mode="validated",
        )

    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)
    output_path = tmp_path / "planning_applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: output_path,
    )
    result = runner.invoke(
        main.app,
        ["--config", str(config_path), "--debug"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    html = output_path.read_text(encoding="utf-8")
    assert "Wards" in html
    assert "Churchill Ward, Hinksey Park" in html


def test_cli_arguments_override_config(
    application_factory: Callable[..., Application], monkeypatch, tmp_path: Path
) -> None:
    """CLI options should override values loaded from config."""
    config_path = tmp_path / "planning_update.toml"
    config_path.write_text(
        "\n".join(
            [
                'ward = "churchill"',
                'status_mode = "validated"',
                'email_to = "config@example.com"',
            ]
        ),
        encoding="utf-8",
    )

    def fake_build_planning_report(*, options) -> PlanningReport:
        query = options.queries[0]
        assert query.ward_name == "marston"
        assert query.status_mode == "decided"
        return build_report_from_applications(
            [application_factory()],
            status_mode="decided",
        )

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
    monkeypatch.setattr(main, "build_planning_report", fake_build_planning_report)
    monkeypatch.setattr(main, "send_resend_email", fake_send_resend_email)

    output_path = tmp_path / "from-cli.html"
    result = runner.invoke(
        main.app,
        [
            "--config",
            str(config_path),
            "--ward",
            "marston",
            "--status",
            "decided",
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
