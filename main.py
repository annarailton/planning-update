"""CLI entry point for the Oxford planning application scraper."""

import argparse
import json
import logging
import sys

import requests
from pydantic import ValidationError

from constants import DEFAULT_WARD_NAME
from models import ApplicationStatusMode, PlanningQuery
from scraper import fetch_latest_applications


def main() -> int:
    """Run the CLI and print the scraped applications as JSON.

    Returns:
        Process exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        description=(
            "Fetch Oxford planning applications for a ward using the "
            "validated-this-week weekly list, optionally falling back to "
            "earlier weeks."
        )
    )
    parser.add_argument(
        "--ward",
        default=DEFAULT_WARD_NAME,
        help=(f"Human-readable ward name to query. Default: {DEFAULT_WARD_NAME!r}."),
    )
    parser.add_argument(
        "--parish",
        help="Optional human-readable parish name to query.",
    )
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--validated",
        action="store_true",
        help="Use the 'Validated in this week' filter. This is the default.",
    )
    date_group.add_argument(
        "--decided",
        action="store_true",
        help="Use the 'Decided in this week' filter.",
    )
    parser.add_argument(
        "--week",
        help="Exact week value from the dropdown, for example '30 Mar 2026'.",
    )
    parser.add_argument(
        "--fallback-weeks",
        type=int,
        default=1,
        help=(
            "How many earlier weeks to try when the latest available week has no "
            "results. Default: 1."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Do not fall back to an earlier week when the first checked week has no results.",
    )
    args = parser.parse_args()

    status_mode: ApplicationStatusMode = "decided" if args.decided else "validated"
    query = PlanningQuery(
        ward_name=args.ward,
        parish_name=args.parish,
        requested_week=args.week,
        fallback_weeks=max(0, args.fallback_weeks),
        strict=args.strict,
        status_mode=status_mode,
    )

    try:
        applications = fetch_latest_applications(query)
    except (ValueError, ValidationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            [
                {
                    "id": application.application_ref.value,
                    "proposal": application.proposal,
                    "url": application.url,
                    "week": application.week,
                }
                for application in applications
            ],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
