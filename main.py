"""CLI entry point for the Oxford planning application scraper."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

import requests
import typer
from pydantic import ValidationError

from config import load_cli_config, resolve_cli_options
from email_sender import (
    build_email_subject,
    build_plain_text_email,
    send_resend_email,
)
from html_render import build_search_criteria, render_application_html
from models import Application, ApplicationSection, CliInputs, CliStatusMode
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

    try:
        options = resolve_cli_options(
            cli_inputs=CliInputs(
                debug=debug,
                ward=ward,
                parish=parish,
                status=status,
                week=week,
                fallback_weeks=fallback_weeks,
                strict=strict,
                output=output,
                email_to=email_to,
            ),
            cli_config=cli_config,
        )
    except ValueError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    section_titles = {
        "validated": "Validated applications",
        "decided": "Decided applications",
    }
    sections: list[ApplicationSection] = []
    applications: list[Application] = []
    try:
        if options.status_mode == "both":
            applications = []
            for query in options.queries:
                section_applications = fetch_latest_applications(query)
                sections.append(
                    ApplicationSection(
                        title=section_titles[query.status_mode],
                        applications=section_applications,
                    )
                )
                applications.extend(section_applications)
        else:
            applications = fetch_latest_applications(options.queries[0])
    except (ValueError, ValidationError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except requests.RequestException as exc:
        typer.secho(f"Request failed: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    generated_at = datetime.now()
    output_path = options.output or build_default_output_path(generated_at=generated_at)
    search_criteria = build_search_criteria(
        query=options.queries[0],
        status_mode=options.status_mode,
    )
    html_output = render_application_html(
        applications,
        sections=sections or None,
        search_criteria=search_criteria,
    )

    typer.echo(f"Found {len(applications)} applications.")

    # We don't send and email and dump results to HTML in debug mode
    if options.debug:
        output_path.write_text(html_output, encoding="utf-8")
        typer.echo(f"Saved HTML output to {output_path}")
        return

    if options.email_recipient:
        subject = build_email_subject(
            week=options.queries[0].requested_week,
        )
        text_output = build_plain_text_email(
            applications=applications,
            sections=sections or None,
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
            recipient=options.email_recipient,
            subject=subject,
            html=html_output,
            text=text_output,
        )
        typer.echo(f"Sent email to {options.email_recipient} via Resend ({email_id}).")


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
