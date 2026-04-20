"""Local cache helpers for planning application query results and details."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..constants import SCRAPER_CACHE_DIR
from ..models import Application, PlanningQuery

APPLICATION_DETAILS_CACHE_DIRNAME = "application-details"
WEEKLY_RESULTS_CACHE_DIRNAME = "weekly-results"
MAJOR_APPLICATIONS_CACHE_FILENAME = "major-applications.json"
APPLICATION_DETAILS_FIELDS = (
    "ward",
    "parish",
    "decided",
    "consultation_deadline",
    "determination_deadline",
    "status",
    "decision",
)
REFRESHABLE_APPLICATION_DETAILS_FIELDS = ("decided", "status", "decision")


def build_query_cache_path(
    query: PlanningQuery, *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> Path:
    """Return the cache filename for a query."""
    cache_key = json.dumps(query.model_dump(mode="json"), sort_keys=True)
    cache_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:16]
    return cache_dir / f"{query.status_mode}_{cache_hash}.json"


def load_cached_applications(
    query: PlanningQuery, *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> list[Application] | None:
    """Load cached applications for a query when present."""
    cache_path = build_query_cache_path(query, cache_dir=cache_dir)
    if not cache_path.exists():
        return None

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    return [Application.model_validate(application) for application in payload]


def save_cached_applications(
    query: PlanningQuery,
    applications: list[Application],
    *,
    cache_dir: Path = SCRAPER_CACHE_DIR,
) -> None:
    """Persist applications for a query to the local cache."""
    cache_path = build_query_cache_path(query, cache_dir=cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            [application.model_dump(mode="json") for application in applications],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def build_weekly_results_cache_path(
    query: PlanningQuery,
    *,
    week: str,
    cache_dir: Path = SCRAPER_CACHE_DIR,
) -> Path:
    """Return the cache filename for shallow weekly-list result cards."""
    cache_payload = query.build_search_payload(csrf_token="", week=week)
    del cache_payload["_csrf"]
    cache_key = json.dumps(cache_payload, sort_keys=True)
    cache_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:16]
    return cache_dir / WEEKLY_RESULTS_CACHE_DIRNAME / f"{cache_hash}.json"


def load_cached_weekly_results(
    query: PlanningQuery,
    *,
    week: str,
    cache_dir: Path = SCRAPER_CACHE_DIR,
) -> list[Application] | None:
    """Load cached shallow weekly-list result cards when present."""
    cache_path = build_weekly_results_cache_path(
        query,
        week=week,
        cache_dir=cache_dir,
    )
    if not cache_path.exists():
        return None

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    return [Application.model_validate(application) for application in payload]


def save_cached_weekly_results(
    query: PlanningQuery,
    applications: list[Application],
    *,
    week: str,
    cache_dir: Path = SCRAPER_CACHE_DIR,
) -> None:
    """Persist shallow weekly-list result cards for one search scope."""
    cache_path = build_weekly_results_cache_path(
        query,
        week=week,
        cache_dir=cache_dir,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            [application.model_dump(mode="json") for application in applications],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def build_major_applications_cache_path(*, cache_dir: Path = SCRAPER_CACHE_DIR) -> Path:
    """Return the cache filename for the Oxford major-applications page."""
    return cache_dir / MAJOR_APPLICATIONS_CACHE_FILENAME


def load_cached_major_applications_payload(
    *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> dict[str, Any] | None:
    """Load the raw major-applications cache payload when present."""
    cache_path = build_major_applications_cache_path(cache_dir=cache_dir)
    if not cache_path.exists():
        return None

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid major applications cache payload: {cache_path}")
    html = payload.get("html")
    cached_at = payload.get("cached_at")
    if not isinstance(html, str) or not isinstance(cached_at, str):
        raise ValueError(f"Invalid major applications cache payload: {cache_path}")
    return {"html": html, "cached_at": cached_at}


def save_cached_major_applications_page(
    html: str, *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> None:
    """Persist the Oxford major-applications page HTML with a cache timestamp."""
    cache_path = build_major_applications_cache_path(cache_dir=cache_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "html": html,
                "cached_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def build_application_details_cache_path(
    application_ref: str, *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> Path:
    """Return the cache filename for one application's enrichment details."""
    safe_ref = application_ref.replace("/", "_")
    return cache_dir / APPLICATION_DETAILS_CACHE_DIRNAME / f"{safe_ref}.json"


def load_cached_application_details(
    application_ref: str, *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> dict[str, Any] | None:
    """Load cached enrichment details for one application when present."""
    payload = load_cached_application_details_payload(
        application_ref,
        cache_dir=cache_dir,
    )
    if payload is None:
        return None
    return payload["details"]


def load_cached_application_details_payload(
    application_ref: str, *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> dict[str, Any] | None:
    """Load the raw cache payload for one application's enrichment details."""
    cache_path = build_application_details_cache_path(
        application_ref,
        cache_dir=cache_dir,
    )
    if not cache_path.exists():
        return None

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid application details cache payload: {cache_path}")

    details = payload.get("details")
    if not isinstance(details, dict):
        raise ValueError(f"Invalid application details cache payload: {cache_path}")
    return {
        "details": details,
        "decision_details_cached_at": payload.get("decision_details_cached_at"),
    }


def save_cached_application_details(
    application: Application, *, cache_dir: Path = SCRAPER_CACHE_DIR
) -> None:
    """Persist non-empty enrichment details for one application reference."""
    cache_path = build_application_details_cache_path(
        application.application_ref.value,
        cache_dir=cache_dir,
    )
    existing_payload = load_cached_application_details_payload(
        application.application_ref.value,
        cache_dir=cache_dir,
    ) or {"details": {}, "decision_details_cached_at": None}
    details_payload = {
        field: value
        for field, value in application.model_dump(mode="json").items()
        if field in APPLICATION_DETAILS_FIELDS and value is not None
    }
    merged_details = existing_payload["details"] | details_payload
    decision_details_cached_at = existing_payload["decision_details_cached_at"]
    if any(
        field in details_payload for field in REFRESHABLE_APPLICATION_DETAILS_FIELDS
    ):
        decision_details_cached_at = datetime.now(UTC).isoformat()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "details": merged_details,
                "decision_details_cached_at": decision_details_cached_at,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
