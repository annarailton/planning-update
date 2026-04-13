"""Tests for the Typer CLI entry point."""

from datetime import date

from typer.testing import CliRunner

import main
from models import Application, ApplicationRef, PlanningQuery

runner = CliRunner()


def test_cli_renders_json_output(monkeypatch) -> None:
    """CLI should print the application count and JSON output."""

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

    result = runner.invoke(main.app, ["--ward", "churchill", "--decided", "--strict"])

    assert result.exit_code == 0
    assert "Found 1 applications." in result.stdout
    assert '"id": "26/00281/FUL"' in result.stdout
    assert '"ward": "Churchill Ward"' in result.stdout
    assert '"decision": "Approved"' in result.stdout


def test_cli_rejects_validated_and_decided_together() -> None:
    """CLI should reject selecting both date mode flags."""
    result = runner.invoke(main.app, ["--validated", "--decided"])

    assert result.exit_code != 0
    assert "Use at most one of --validated or --decided." in result.output
