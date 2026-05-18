"""CLI entry point for the Oxford planning application scraper."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

import requests
import typer
from dotenv import load_dotenv
from pydantic import ValidationError

from .config import load_cli_config, resolve_cli_options
from .integrations.email_sender import (
    build_default_email_log_path,
    build_email_subject,
    build_plain_text_email,
    send_resend_email,
    write_sent_email_log,
)
from .models import CliInputs, CliStatusMode
from .renderers.html_render import build_search_criteria, render_application_html
from .services.report_service import build_planning_report

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


def resolve_resend_api_key(*, needs_email: bool) -> str | None:
    """Load and return the Resend API key when email sending is requested."""
    if not needs_email:
        return None

    load_dotenv()
    resend_api_key = os.environ.get("RESEND_API_KEY")
    if not resend_api_key:
        raise typer.BadParameter("RESEND_API_KEY must be set when using --email-to.")
    return resend_api_key


@app.callback()
def run(
    config: Annotated[
        Path | None,
        typer.Option(
            help=("Optional TOML config file to load CLI defaults from."),
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
        list[str] | None,
        typer.Option(
            help=(
                "Optional human-readable ward name to query. Repeat --ward to "
                "search multiple wards. Defaults to all wards."
            )
        ),
    ] = None,
    parish: Annotated[
        str | None,
        typer.Option(
            help="Optional human-readable parish name to query. Defaults to all parishes."
        ),
    ] = None,
    status: Annotated[
        CliStatusMode | None,
        typer.Option(
            "--status",
            help="Which weekly list to query: validated, decided, or both.",
        ),
    ] = None,
    week: Annotated[
        str | None,
        typer.Option(
            help="Exact week value from the dropdown, for example '30 Mar 2026'."
        ),
    ] = None,
    keywords: Annotated[
        str | None,
        typer.Option(
            "--keywords",
            help="Comma-delimited proposal keywords to match across all wards and parishes.",
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
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(message)s",
    )

    try:
        cli_config = load_cli_config(path=config)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    try:
        options = resolve_cli_options(
            cli_inputs=CliInputs(
                debug=debug,
                ward=ward,
                parish=parish,
                status=status,
                week=week,
                keywords=keywords,
                email_to=email_to,
            ),
            cli_config=cli_config,
        )
    except ValueError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    # Fail fast if we don't have an email API key when email sending is requested
    try:
        resend_api_key = resolve_resend_api_key(
            needs_email=options.email_recipient is not None and not options.debug
        )
    except typer.BadParameter as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    try:
        report = build_planning_report(options=options)
    except (ValueError, ValidationError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except requests.RequestException as exc:
        typer.secho(f"Request failed: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    generated_at = datetime.now()
    output_path = build_default_output_path(generated_at=generated_at)
    search_criteria = build_search_criteria(
        options=options,
        actual_week=report.actual_week,
    )
    html_output = render_application_html(
        report.applications,
        sections=report.sections,
        search_criteria=search_criteria,
    )

    typer.echo(f"Found {len(report.applications)} applications.")

    if options.debug:
        output_path.write_text(html_output, encoding="utf-8")
        typer.echo(f"Saved HTML output to {output_path}")
        return

    if options.email_recipient:
        subject = build_email_subject(
            week=options.queries[0].requested_week,
        )
        text_output = build_plain_text_email(
            applications=report.applications,
            sections=report.sections,
            generated_at=generated_at,
            search_criteria=search_criteria,
        )

        email_id = send_resend_email(
            api_key=resend_api_key,
            recipient=options.email_recipient,
            subject=subject,
            html=html_output,
            text=text_output,
        )
        sent_at = datetime.now()
        email_log_path = write_sent_email_log(
            html=html_output,
            sent_at=sent_at,
            config_path=config,
            log_path=build_default_email_log_path(
                sent_at=sent_at,
                config_path=config,
            ),
        )
        typer.echo(f"Sent email to {options.email_recipient} via Resend ({email_id}).")
        typer.echo(f"Saved sent email HTML to {email_log_path}")


def main() -> None:
    """Run the Typer application."""
    app()
