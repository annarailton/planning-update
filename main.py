"""CLI entry point for the Oxford planning application scraper."""

import json
import logging
from typing import Annotated

import requests
import typer
from pydantic import ValidationError

from models import ApplicationStatusMode, PlanningQuery
from scraper import fetch_latest_applications

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False,
    help=("Fetch Oxford planning applications for a ward using the weekly list"),
)


@app.callback()
def run(
    ward: Annotated[
        str | None,
        typer.Option(
            help="Optional human-readable ward name to query. Defaults to all wards."
        ),
    ] = None,
    parish: Annotated[
        str | None,
        typer.Option(
            help="Optional human-readable parish name to query. Defaults to all parishes."
        ),
    ] = None,
    validated: Annotated[
        bool,
        typer.Option(
            help="Use the 'Validated in this week' filter. This is the default."
        ),
    ] = False,
    decided: Annotated[
        bool,
        typer.Option(help="Use the 'Decided in this week' filter."),
    ] = False,
    week: Annotated[
        str | None,
        typer.Option(
            help="Exact week value from the dropdown, for example '30 Mar 2026'."
        ),
    ] = None,
    fallback_weeks: Annotated[
        int,
        typer.Option(
            help=(
                "How many earlier weeks to try when the latest available week has no "
                "results. Default: 1."
            )
        ),
    ] = 1,
    strict: Annotated[
        bool,
        typer.Option(
            help="Do not fall back to an earlier week when the first checked week has no results."
        ),
    ] = False,
) -> None:
    """Run the CLI and print the scraped applications as JSON."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if validated and decided:
        raise typer.BadParameter("Use at most one of --validated or --decided.")

    status_mode: ApplicationStatusMode = "decided" if decided else "validated"
    query = PlanningQuery(
        ward_name=ward,
        parish_name=parish,
        requested_week=week,
        fallback_weeks=max(0, fallback_weeks),
        strict=strict,
        status_mode=status_mode,
    )

    try:
        applications = fetch_latest_applications(query)
    except (ValueError, ValidationError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except requests.RequestException as exc:
        typer.secho(f"Request failed: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Found {len(applications)} applications.")
    if not applications:
        return
    typer.echo(
        json.dumps(
            [
                {
                    "id": application.application_ref.value,
                    "proposal": application.proposal,
                    "url": application.url,
                    "address": application.address,
                    "ward": application.ward,
                    "parish": application.parish,
                    "received": application.received.isoformat(),
                    "validated": application.validated.isoformat(),
                    "decided": (
                        application.decided.isoformat()
                        if application.decided is not None
                        else None
                    ),
                    "consultation_deadline": (
                        application.consultation_deadline.isoformat()
                        if application.consultation_deadline is not None
                        else None
                    ),
                    "determination_deadline": (
                        application.determination_deadline.isoformat()
                        if application.determination_deadline is not None
                        else None
                    ),
                    "status": application.status,
                    "decision": application.decision,
                }
                for application in applications
            ],
            indent=2,
        )
    )


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
