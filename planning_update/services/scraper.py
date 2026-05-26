"""High-level scraping and enrichment workflow for planning applications."""

import logging
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

from ..constants import (
    APPLICATION_DETAILS_DECISION_TTL_SECONDS,
    ENRICHMENT_REQUEST_DELAY_SECONDS,
    MAJOR_APPLICATIONS_CACHE_TTL_SECONDS,
    SCRAPER_CACHE_DIR,
)
from ..lookup.postcode_lookup import (
    lookup_postcode_in_oxford_wards,
    postcode_is_within_division_distance,
    postcode_is_within_parish_distance,
    postcode_is_within_ward_distance,
)
from ..models import Application, PlanningQuery
from ..parsing.parser import (
    extract_applications,
    extract_important_dates,
    extract_major_application_refs,
    extract_pagination_urls,
    extract_summary_fields,
)
from .cache import (
    load_cached_application_details_payload,
    load_cached_applications,
    load_cached_major_applications_payload,
    load_cached_weekly_results,
    save_cached_application_details,
    save_cached_applications,
    save_cached_major_applications_page,
    save_cached_weekly_results,
)
from .oxford_planning_client import (
    build_dates_tab_url,
    fetch_form,
    fetch_major_applications_page,
    fetch_page,
    fetch_results_page,
    resolve_actual_week,
)

logger = logging.getLogger(__name__)


def enrich_application(
    session: requests.Session,
    application: Application,
    *,
    query: PlanningQuery,
    cache_dir: Path = SCRAPER_CACHE_DIR,
) -> Application:
    """Fetch and attach summary-only fields and important dates.

    Args:
        session: HTTP session used to request the Oxford planning site.
        application: Parsed application to enrich.
        query: Query mode used to decide which extra pages are required.
        cache_dir: Local cache directory for enrichment results when available.

    Returns:
        The application with summary-only fields and important dates populated
        when available. Ward and parish are derived locally from postcode data.
    """
    cached_details_payload = load_cached_application_details_payload(
        application.application_ref.value,
        cache_dir=cache_dir,
    )
    cached_details = None
    decision_details_are_stale = True
    if cached_details_payload is not None:
        cached_details = cached_details_payload["details"]
        logger.info(
            "Cache hit: application details for %s",
            application.application_ref.value,
        )
        application = Application.model_validate(
            application.model_dump(mode="json") | cached_details
        )
        decision_details_are_stale = cached_timestamp_is_stale(
            cached_details_payload.get("decision_details_cached_at"),
            ttl_seconds=APPLICATION_DETAILS_DECISION_TTL_SECONDS,
        )

    request_count = 0

    def fetch_enrichment_page(page_url: str) -> str:
        """Fetch one enrichment page with a short pause between requests.

        This is to be nice to the planning site. There can be a lot of
        enrichment requests.
        """
        nonlocal request_count
        if request_count > 0:
            time.sleep(ENRICHMENT_REQUEST_DELAY_SECONDS)
        request_count += 1
        page_html, _ = fetch_page(session, page_url)
        return page_html

    updated_fields: dict[str, object] = {}
    if application.postcode is not None and (
        application.ward is None
        or application.parish is None
        or application.division is None
    ):
        try:
            postcode_lookup = lookup_postcode_in_oxford_wards(application.postcode)
        except ValueError:
            postcode_lookup = None
        if postcode_lookup is not None:
            if application.ward is None:
                updated_fields["ward"] = postcode_lookup.ward_name
            if application.parish is None:
                updated_fields["parish"] = postcode_lookup.parish_name
            if application.division is None:
                updated_fields["division"] = getattr(
                    postcode_lookup,
                    "division_name",
                    None,
                )

    decision_fields_missing = (
        application.status is None
        or application.decided is None
        or application.decision is None
    )
    if query.status_mode == "decided" and (
        decision_fields_missing or decision_details_are_stale
    ):
        summary_html = fetch_enrichment_page(application.url)
        status, decided, decision = extract_summary_fields(summary_html)
        updated_fields["status"] = status
        updated_fields["decided"] = decided
        updated_fields["decision"] = decision

    if query.status_mode == "validated" and (
        application.consultation_deadline is None
        or application.determination_deadline is None
    ):
        dates_html = fetch_enrichment_page(build_dates_tab_url(application.url))
        consultation_deadline, determination_deadline = extract_important_dates(
            dates_html
        )
        updated_fields["consultation_deadline"] = consultation_deadline
        updated_fields["determination_deadline"] = determination_deadline

    if not updated_fields:
        return application

    enriched_application = Application.model_validate(
        application.model_dump() | updated_fields
    )
    save_cached_application_details(enriched_application, cache_dir=cache_dir)
    return enriched_application


def cached_timestamp_is_stale(cached_at: str | None, *, ttl_seconds: int) -> bool:
    """Return whether a cached timestamp is missing, invalid, or older than a TTL."""
    if not cached_at:
        return True

    try:
        cached_at_dt = datetime.fromisoformat(cached_at)
    except ValueError:
        return True

    if cached_at_dt.tzinfo is None:
        cached_at_dt = cached_at_dt.replace(tzinfo=UTC)

    age_seconds = (datetime.now(UTC) - cached_at_dt).total_seconds()
    return age_seconds >= ttl_seconds


def load_major_applications_page(
    session: requests.Session,
    *,
    cache_dir: Path = SCRAPER_CACHE_DIR,
) -> str:
    """Load the Oxford major-applications page, reusing the local cache when fresh."""
    cached_payload = load_cached_major_applications_payload(cache_dir=cache_dir)
    if cached_payload is not None and not cached_timestamp_is_stale(
        cached_payload["cached_at"],
        ttl_seconds=MAJOR_APPLICATIONS_CACHE_TTL_SECONDS,
    ):
        logger.info("Cache hit: major applications page")
        return cached_payload["html"]

    html = fetch_major_applications_page(session)
    save_cached_major_applications_page(html, cache_dir=cache_dir)
    return html


def filter_applications_by_keywords(
    applications: list[Application], *, query: PlanningQuery
) -> list[Application]:
    """Filter result-card applications to proposal keyword matches when configured."""
    if not query.uses_keyword_matching():
        return applications

    matched_applications: list[Application] = []
    for application in applications:
        keyword_matches = query.matching_keywords(application.proposal)
        if not keyword_matches:
            continue
        matched_applications.append(
            Application.model_validate(
                application.model_dump() | {"keyword_matches": keyword_matches}
            )
        )
    return matched_applications


def filter_applications_by_major_refs(
    applications: list[Application],
    *,
    major_refs: set[str],
) -> list[Application]:
    """Filter result-card applications to those on the current major list."""
    matched_applications: list[Application] = []
    for application in applications:
        if application.application_ref.value not in major_refs:
            continue
        matched_applications.append(
            Application.model_validate(
                application.model_dump() | {"is_major_application": True}
            )
        )
    return matched_applications


def filter_applications_by_major(
    session: requests.Session,
    applications: list[Application],
    *,
    query: PlanningQuery,
    cache_dir: Path = SCRAPER_CACHE_DIR,
) -> list[Application]:
    """Filter applications to current Oxford major applications when configured.

    This wrapper exists to keep `fetch_latest_applications` compact and readable
    """
    if not query.uses_major_matching():
        return applications

    major_application_refs = {
        application_ref.value
        for application_ref in extract_major_application_refs(
            load_major_applications_page(session, cache_dir=cache_dir)
        )
    }
    return filter_applications_by_major_refs(
        applications,
        major_refs=major_application_refs,
    )


def filter_applications_by_ward_distance(
    applications: list[Application], *, query: PlanningQuery
) -> list[Application]:
    """Filter applications to those matching the configured location scope."""
    if (
        query.ward_name is None
        and query.parish_name is None
        and query.division_name is None
    ):
        return applications

    matching_applications: list[Application] = []
    target_ward_name = (
        query.resolved_ward_name() if query.ward_name is not None else None
    )
    target_parish_name = (
        query.resolved_parish_name() if query.parish_name is not None else None
    )
    target_division_name = (
        query.resolved_division_name() if query.division_name is not None else None
    )
    target_ward_label = (
        query.ward_name
        if query.ward_name is not None and query.uses_distance_around_ward()
        else None
    )
    target_parish_label = (
        query.parish_name
        if query.parish_name is not None and query.uses_distance_around_parish()
        else None
    )
    target_division_label = (
        query.division_name
        if query.division_name is not None and query.uses_distance_around_division()
        else None
    )
    ward_distance_label = (
        query.distance_around_ward_label if query.uses_distance_around_ward() else None
    )
    parish_distance_label = (
        query.distance_around_parish_label
        if query.uses_distance_around_parish()
        else None
    )
    division_distance_label = (
        query.distance_around_division_label
        if query.uses_distance_around_division()
        else None
    )
    for application in applications:
        if application.postcode is None:
            continue
        try:
            postcode_lookup = None
            matches_ward = True
            if target_ward_name is not None:
                if query.uses_distance_around_ward():
                    matches_ward = postcode_is_within_ward_distance(
                        application.postcode,
                        target_ward_name,
                        distance_meters=query.distance_around_ward_meters,
                    )
                else:
                    postcode_lookup = lookup_postcode_in_oxford_wards(
                        application.postcode
                    )
                    matches_ward = postcode_lookup.ward_name == target_ward_name

            matches_parish = True
            if target_parish_name is not None:
                if query.uses_distance_around_parish():
                    matches_parish = postcode_is_within_parish_distance(
                        application.postcode,
                        target_parish_name,
                        distance_meters=query.distance_around_parish_meters,
                    )
                else:
                    if postcode_lookup is None:
                        postcode_lookup = lookup_postcode_in_oxford_wards(
                            application.postcode
                        )
                    matches_parish = postcode_lookup.parish_name == target_parish_name

            matches_division = True
            if target_division_name is not None:
                if query.uses_distance_around_division():
                    matches_division = postcode_is_within_division_distance(
                        application.postcode,
                        target_division_name,
                        distance_meters=query.distance_around_division_meters,
                    )
                else:
                    if postcode_lookup is None:
                        postcode_lookup = lookup_postcode_in_oxford_wards(
                            application.postcode
                        )
                    matches_division = (
                        getattr(postcode_lookup, "division_name", None)
                        == target_division_name
                    )

            if matches_ward and matches_parish and matches_division:
                inclusion_reasons: list[str] = []
                if target_ward_label is not None and ward_distance_label is not None:
                    inclusion_reasons.append(
                        f"{target_ward_label} + {ward_distance_label}"
                    )
                if (
                    target_parish_label is not None
                    and parish_distance_label is not None
                ):
                    inclusion_reasons.append(
                        f"{target_parish_label} + {parish_distance_label}"
                    )
                if (
                    target_division_label is not None
                    and division_distance_label is not None
                ):
                    inclusion_reasons.append(
                        f"{target_division_label} + {division_distance_label}"
                    )
                matching_applications.append(
                    Application.model_validate(
                        application.model_dump()
                        | {
                            "inclusion_reason": ", ".join(inclusion_reasons) or None,
                        }
                    )
                )
        except ValueError:
            continue

    return matching_applications


def collect_result_applications(
    session: requests.Session,
    *,
    query: PlanningQuery,
    cache_dir: Path = SCRAPER_CACHE_DIR,
    selected_week: str | None = None,
) -> tuple[list[Application], str]:
    """Collect shallow weekly-list applications for the whole selected week/status."""
    week = selected_week
    if week is None:
        _, weeks = fetch_form(session)
        week = query.selected_week(weeks)
    weekly_list_query = PlanningQuery(
        requested_week=week,
        status_mode=query.status_mode,
    )
    cached_applications = load_cached_weekly_results(
        weekly_list_query,
        week=week,
        cache_dir=cache_dir,
    )
    if cached_applications is not None:
        logger.info(
            "Cache hit: weekly results for %s (%s)",
            week,
            query.status_mode,
        )
        return cached_applications, week

    csrf_token, _ = fetch_form(session)

    html, page_url = fetch_results_page(
        session,
        query=weekly_list_query,
        csrf_token=csrf_token,
        week=week,
    )
    applications = extract_applications(html, week, page_url)
    for pagination_url in extract_pagination_urls(html, page_url):
        next_html, next_page_url = fetch_page(session, pagination_url)
        applications.extend(extract_applications(next_html, week, next_page_url))
    save_cached_weekly_results(
        weekly_list_query,
        applications,
        week=week,
        cache_dir=cache_dir,
    )
    return applications, week


def fetch_latest_applications(
    query: PlanningQuery,
    *,
    cache_dir: Path = SCRAPER_CACHE_DIR,
    selected_week: str | None = None,
) -> tuple[list[Application], str]:
    """Fetch applications for the selected or latest available week.

    Args:
        query: User-facing query options for the weekly list search.
        cache_dir: Local cache directory for enrichment results when available.
        selected_week: When provided, skip the week selection step and use this

    Returns:
        A tuple of ``(applications, week)`` where ``week`` is the actual
        weekly-list label selected from the Oxford form.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": "planning-update/0.1"})

    applications, week = collect_result_applications(
        session,
        query=query,
        cache_dir=cache_dir,
        selected_week=selected_week,
    )
    applications = filter_applications_by_keywords(applications, query=query)
    applications = filter_applications_by_major(
        session,
        applications,
        query=query,
        cache_dir=cache_dir,
    )
    applications = filter_applications_by_ward_distance(applications, query=query)
    return (
        [
            enrich_application(
                session,
                application,
                query=query,
                cache_dir=cache_dir,
            )
            for application in applications
        ],
        week,
    )


def fetch_latest_applications_cached(
    query: PlanningQuery,
    *,
    cache_dir: Path = SCRAPER_CACHE_DIR,
    selected_week: str | None = None,
) -> list[Application]:
    """Fetch applications for a query, reusing the local cache when available."""
    cached_applications = load_cached_applications(query, cache_dir=cache_dir)
    if cached_applications is not None:
        logger.info("Cache hit: query results for %s", query.model_dump(mode="json"))
        return cached_applications

    applications, _ = fetch_latest_applications(
        query,
        cache_dir=cache_dir,
        selected_week=selected_week,
    )
    save_cached_applications(query, applications, cache_dir=cache_dir)
    return applications


def fetch_applications_for_query(
    *, query: PlanningQuery, debug: bool, actual_week: str | None = None
) -> tuple[list[Application], str | None]:
    """Fetch applications plus the actual selected week when available."""
    return fetch_latest_applications(query, selected_week=actual_week)
