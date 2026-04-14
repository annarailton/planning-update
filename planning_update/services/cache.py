"""Local cache helpers for planning application query results."""

import hashlib
import json
from pathlib import Path

from ..constants import SCRAPER_CACHE_DIR
from ..models import Application, PlanningQuery


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
