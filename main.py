"""CLI entry point for the Oxford planning application scraper."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

import requests
import typer
from pydantic import ValidationError

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
    output: Annotated[
        Path | None,
        typer.Option(
            help="Optional path to write the rendered HTML output file.",
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
    dry_run_email: Annotated[
        bool,
        typer.Option(
            help="Build the email payload but do not send it to Resend.",
        ),
    ] = False,
) -> None:
    """Run the CLI and write the scraped applications to an HTML file."""
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

    generated_at = datetime.now()
    output_path = output or build_default_output_path(generated_at=generated_at)
    search_criteria = build_search_criteria(
        query=query,
        validated=validated,
        decided=decided,
    )
    html_output = render_application_html(
        applications,
        search_criteria=search_criteria,
    )

    typer.echo(f"Found {len(applications)} applications.")
    if not applications:
        return
    output_path.write_text(html_output, encoding="utf-8")
    typer.echo(f"Saved HTML output to {output_path}")

    if email_to:
        subject = build_email_subject(
            week=query.requested_week,
        )
        text_output = build_plain_text_email(
            applications=applications,
            generated_at=generated_at,
            search_criteria=search_criteria,
        )

        if dry_run_email:
            typer.echo(
                f"Dry run: prepared email to {email_to} with subject '{subject}'."
            )
            return

        resend_api_key = os.environ.get("RESEND_API_KEY")
        if not resend_api_key:
            raise typer.BadParameter(
                "RESEND_API_KEY must be set when using --email-to."
            )

        email_id = send_resend_email(
            api_key=resend_api_key,
            recipient=email_to,
            subject=subject,
            html=html_output,
            text=text_output,
        )
        typer.echo(f"Sent email to {email_to} via Resend ({email_id}).")


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
