"""CLI entry point for the Oxford planning application scraper."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

import requests
import typer
from pydantic import ValidationError

from config import load_cli_config
from email_sender import (
    build_email_subject,
    build_plain_text_email,
    send_resend_email,
)
from html_render import build_search_criteria, render_application_html
from models import ApplicationStatusMode, PlanningQuery
from scraper import fetch_latest_applications

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
    help=("Fetch Oxford planning applications for a ward using the weekly list"),
)


def build_default_output_path(*, generated_at: datetime) -> Path:
    """Build the default output filename with an ISO-like timestamp slug."""
    timestamp_slug = generated_at.strftime("%Y-%m-%dT%H-%M-%S")
    return Path(f"{timestamp_slug}_planning_applications.html")


@app.callback()
def run(
    config: Annotated[
        Path | None,
        typer.Option(
            help=(
                "Optional TOML config file to load CLI defaults from. "
                "Defaults to planning_update.toml when present."
            ),
            dir_okay=False,
            exists=False,
        ),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Write the rendered HTML output to a local file for inspection.",
        ),
    ] = False,
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
        bool | None,
        typer.Option(
            "--validated/--no-validated",
            help="Use the 'Validated in this week' filter. This is the default.",
        ),
    ] = None,
    decided: Annotated[
        bool | None,
        typer.Option(
            "--decided/--no-decided",
            help="Use the 'Decided in this week' filter.",
        ),
    ] = None,
    week: Annotated[
        str | None,
        typer.Option(
            help="Exact week value from the dropdown, for example '30 Mar 2026'."
        ),
    ] = None,
    fallback_weeks: Annotated[
        int | None,
        typer.Option(
            help=(
                "How many earlier weeks to try when the latest available week has no "
                "results. Default: 1."
            )
        ),
    ] = None,
    strict: Annotated[
        bool | None,
        typer.Option(
            "--strict/--no-strict",
            help="Do not fall back to an earlier week when the first checked week has no results.",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            help="Optional path for the debug HTML output file.",
            dir_okay=False,
            writable=True,
        ),
    ] = None,
    email_to: Annotated[
        str | None,
        typer.Option(
            help="Optional recipient email address to send the rendered HTML via Resend.",
        ),
    ] = None,
) -> None:
    """Run the CLI and write the scraped applications to an HTML file."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        cli_config = load_cli_config(path=config)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if validated is True and decided is True:
        raise typer.BadParameter("Use at most one of --validated or --decided.")

    if decided is True:
        status_mode: ApplicationStatusMode = "decided"
    elif validated is True:
        status_mode = "validated"
    elif cli_config.status_mode is not None:
        status_mode = cli_config.status_mode
    else:
        status_mode = "validated"

    fallback_weeks_value = (
        fallback_weeks
        if fallback_weeks is not None
        else cli_config.fallback_weeks if cli_config.fallback_weeks is not None else 1
    )
    debug = debug or cli_config.debug is True
    strict_value = (
        strict
        if strict is not None
        else cli_config.strict if cli_config.strict is not None else False
    )
    output_path = output or cli_config.output
    email_recipient = email_to if email_to is not None else cli_config.email_to

    query = PlanningQuery(
        ward_name=ward if ward is not None else cli_config.ward,
        parish_name=parish if parish is not None else cli_config.parish,
        requested_week=week if week is not None else cli_config.week,
        fallback_weeks=max(0, fallback_weeks_value),
        strict=strict_value,
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

    generated_at = datetime.now()
    output_path = output_path or build_default_output_path(generated_at=generated_at)
    search_criteria = build_search_criteria(
        query=query,
        validated=status_mode == "validated",
        decided=status_mode == "decided",
    )
    html_output = render_application_html(
        applications,
        search_criteria=search_criteria,
    )

    typer.echo(f"Found {len(applications)} applications.")
    if not applications:
        return

    # We don't send and email and dump results to HTML in debug mode
    if debug:
        output_path = output_path or build_default_output_path(
            generated_at=generated_at
        )
        output_path.write_text(html_output, encoding="utf-8")
        typer.echo(f"Saved HTML output to {output_path}")
        return

    if email_recipient:
        subject = build_email_subject(
            week=query.requested_week,
        )
        text_output = build_plain_text_email(
            applications=applications,
            generated_at=generated_at,
            search_criteria=search_criteria,
        )

        resend_api_key = os.environ.get("RESEND_API_KEY")
        if not resend_api_key:
            raise typer.BadParameter(
                "RESEND_API_KEY must be set when using --email-to."
            )

        email_id = send_resend_email(
            api_key=resend_api_key,
            recipient=email_recipient,
            subject=subject,
            html=html_output,
            text=text_output,
        )
        typer.echo(f"Sent email to {email_recipient} via Resend ({email_id}).")


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
