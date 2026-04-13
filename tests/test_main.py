"""Tests for the Typer CLI entry point."""

import re
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

import main
from models import Application, ApplicationRef, PlanningQuery

runner = CliRunner()
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def test_cli_writes_html_output_file(monkeypatch, tmp_path: Path) -> None:
    """CLI should print the application count and write HTML card output to a file."""

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        assert query.ward_name == "churchill"
        assert query.status_mode == "decided"
        assert query.strict is True
        return [
            Application(
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
        ]

    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )

    output_path = tmp_path / "applications.html"
    result = runner.invoke(
        main.app,
        [
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


def test_cli_uses_timestamped_default_output_filename(
    monkeypatch, tmp_path: Path
) -> None:
    """CLI should use a timestamped HTML filename when output is not provided."""

    def fake_fetch_latest_applications(query: PlanningQuery) -> list[Application]:
        return [
            Application(
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
        ]

    monkeypatch.setattr(
        main, "fetch_latest_applications", fake_fetch_latest_applications
    )

    default_output_path = tmp_path / "2026-04-13T09-30-00_planning_applications.html"
    monkeypatch.setattr(
        main,
        "build_default_output_path",
        lambda *, generated_at: default_output_path,
    )

    result = runner.invoke(main.app, ["--decided"], catch_exceptions=False)

    assert result.exit_code == 0
    assert f"Saved HTML output to {default_output_path}" in result.stdout
    assert default_output_path.exists()


def test_cli_rejects_validated_and_decided_together() -> None:
    """CLI should reject selecting both date mode flags."""
    result = runner.invoke(main.app, ["--validated", "--decided"])
    # Typer may emit ANSI styling in CI, so normalize before asserting on text.
    output = ANSI_ESCAPE_RE.sub("", result.output)

    assert result.exit_code != 0
    assert "Use at most one of --validated or --decided." in output
