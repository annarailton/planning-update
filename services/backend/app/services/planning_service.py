"""Service for fetching Oxford weekly planning applications."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin

import httpx

from core.exceptions import ExternalAPIError, ServiceError, ValidationError
from core.logging import get_logger
from schemas.planning import (
    PlanningApplicationAvailableFilters,
    PlanningApplicationDateType,
    PlanningApplicationFilters,
    PlanningApplicationSearchResponse,
    PlanningApplicationSummary,
    PlanningFilterOption,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class _ResolvedFilters:
    csrf_token: str
    ward_code: str | None
    ward_label: str | None
    week_beginning: str
    ward_options: list[PlanningFilterOption]
    week_options: list[str]


class PlanningService:
    """Fetch and normalize weekly planning applications from Oxford City Council."""

    base_url = "https://public.oxford.gov.uk"
    weekly_list_path = "/online-applications/search.do?action=weeklyList"
    weekly_results_path = "/online-applications/weeklyListResults.do?action=firstPage"

    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 20.0,
    ) -> None:
        self._transport = transport
        self._timeout = timeout

    async def get_weekly_applications(
        self,
        *,
        ward: str | None = None,
        week_beginning: str | None = None,
        date_type: PlanningApplicationDateType = PlanningApplicationDateType.VALIDATED,
    ) -> PlanningApplicationSearchResponse:
        """Fetch weekly planning applications for the given filters."""
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                follow_redirects=True,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                form_response = await client.get(self.weekly_list_path)
                form_response.raise_for_status()
                resolved = self._resolve_filters(
                    form_response.text, ward=ward, week_beginning=week_beginning
                )
                payload = {
                    "_csrf": resolved.csrf_token,
                    "searchCriteria.ward": resolved.ward_code or "",
                    "week": resolved.week_beginning,
                    "dateType": self._map_date_type(date_type),
                    "searchType": "Application",
                }
                response = await client.post(self.weekly_results_path, data=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ExternalAPIError("Oxford planning", "Request timed out") from exc
        except httpx.HTTPError as exc:
            raise ExternalAPIError("Oxford planning", "Request failed") from exc

        html = response.text
        if self._is_search_results_page(html):
            applications = self._parse_search_results(
                html, default_ward=resolved.ward_label
            )
        elif self._is_application_summary_page(html):
            applications = [
                self._parse_application_summary(
                    html,
                    detail_url=str(response.url),
                    default_ward=resolved.ward_label,
                )
            ]
        else:
            logger.error("Unexpected Oxford planning response format")
            raise ServiceError(
                "Oxford planning response format changed",
                detail="Could not identify search results or application summary markup",
                status_code=502,
            )

        return PlanningApplicationSearchResponse(
            applications=applications,
            total_count=len(applications),
            filters=PlanningApplicationFilters(
                ward=resolved.ward_label,
                week_beginning=resolved.week_beginning,
                date_type=date_type,
            ),
            available_filters=PlanningApplicationAvailableFilters(
                wards=resolved.ward_options,
                weeks=resolved.week_options,
            ),
        )

    def _resolve_filters(
        self, form_html: str, *, ward: str | None, week_beginning: str | None
    ) -> _ResolvedFilters:
        """Resolve user-friendly filters to source values."""
        csrf_token = self._extract_input_value(form_html, "_csrf")
        ward_options = self._extract_select_options(form_html, "ward")
        week_options = [
            option.label for option in self._extract_select_options(form_html, "week")
        ]

        if not week_options:
            raise ServiceError(
                "Oxford planning weekly list has no available weeks",
                status_code=502,
            )

        ward_code: str | None = None
        ward_label: str | None = None
        if ward:
            ward_match = self._match_option(ward_options, ward)
            if not ward_match:
                raise ValidationError(
                    f"Unknown ward '{ward}'",
                    detail={
                        "available_wards": [option.label for option in ward_options]
                    },
                )
            ward_code = ward_match.value
            ward_label = ward_match.label

        resolved_week = week_beginning or week_options[0]
        if resolved_week not in week_options:
            raise ValidationError(
                f"Unknown week '{resolved_week}'",
                detail={"available_weeks": week_options},
            )

        return _ResolvedFilters(
            csrf_token=csrf_token,
            ward_code=ward_code,
            ward_label=ward_label,
            week_beginning=resolved_week,
            ward_options=ward_options,
            week_options=week_options,
        )

    @staticmethod
    def _map_date_type(date_type: PlanningApplicationDateType) -> str:
        """Map API enum values to Oxford form values."""
        if date_type == PlanningApplicationDateType.DECIDED:
            return "DC_Decided"
        return "DC_Validated"

    @staticmethod
    def _extract_input_value(html: str, name: str) -> str:
        """Extract an input value by name."""
        pattern = rf'<input[^>]+name="{re.escape(name)}"[^>]+value="([^"]*)"'
        match = re.search(pattern, html)
        if not match:
            raise ServiceError(
                f"Oxford planning form is missing '{name}'",
                status_code=502,
            )
        return unescape(match.group(1).strip())

    @staticmethod
    def _extract_select_options(
        html: str, select_id: str
    ) -> list[PlanningFilterOption]:
        """Extract options for a select by id."""
        select_match = re.search(
            rf'<select[^>]+id="{re.escape(select_id)}"[^>]*>(.*?)</select>',
            html,
            re.DOTALL,
        )
        if not select_match:
            return []

        options: list[PlanningFilterOption] = []
        for value, label in re.findall(
            r'<option value="([^"]*)"(?:[^>]*)>(.*?)</option>',
            select_match.group(1),
            re.DOTALL,
        ):
            clean_label = PlanningService._clean_html_text(label)
            if not value or not clean_label or clean_label == "All":
                continue
            options.append(
                PlanningFilterOption(value=unescape(value.strip()), label=clean_label)
            )
        return options

    @staticmethod
    def _match_option(
        options: list[PlanningFilterOption], query: str
    ) -> PlanningFilterOption | None:
        """Match a query against option value or label."""
        normalized_query = PlanningService._normalize_option(query)
        for option in options:
            if normalized_query in {
                PlanningService._normalize_option(option.value),
                PlanningService._normalize_option(option.label),
            }:
                return option
        return None

    @staticmethod
    def _normalize_option(value: str) -> str:
        """Normalize filter option input for comparison."""
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    @staticmethod
    def _is_search_results_page(html: str) -> bool:
        """Check whether the response is a search-results page."""
        return 'id="searchresults"' in html

    @staticmethod
    def _is_application_summary_page(html: str) -> bool:
        """Check whether the response is a single-application summary page."""
        return 'id="simpleDetailsTable"' in html

    @classmethod
    def _parse_search_results(
        cls, html: str, *, default_ward: str | None
    ) -> list[PlanningApplicationSummary]:
        """Parse a list-style search results page."""
        results_section = re.search(
            r'<ul id="searchresults">(.*?)</ul>',
            html,
            re.DOTALL,
        )
        if not results_section:
            return []

        applications: list[PlanningApplicationSummary] = []
        for item_html in re.findall(
            r'<li class="searchresult">(.*?)</li>',
            results_section.group(1),
            re.DOTALL,
        ):
            link_match = re.search(
                r'<a href="([^"]+)" class="summaryLink">.*?<div class="summaryLinkTextClamp">(.*?)</div>',
                item_html,
                re.DOTALL,
            )
            reference_match = re.search(r"Ref\. No:\s*([A-Z0-9/]+)", item_html)
            address_match = re.search(
                r'<p class="address">(.*?)</p>',
                item_html,
                re.DOTALL,
            )

            if not (link_match and reference_match and address_match):
                logger.warning("Skipping Oxford planning result with incomplete markup")
                continue

            applications.append(
                PlanningApplicationSummary(
                    application_id=cls._clean_html_text(reference_match.group(1)),
                    location=cls._clean_html_text(address_match.group(1)),
                    ward=default_ward,
                    summary=cls._clean_html_text(link_match.group(2)),
                    detail_url=urljoin(cls.base_url, unescape(link_match.group(1))),
                )
            )

        return applications

    @classmethod
    def _parse_application_summary(
        cls,
        html: str,
        *,
        detail_url: str,
        default_ward: str | None,
    ) -> PlanningApplicationSummary:
        """Parse a single application-summary page."""
        table_match = re.search(
            r'<table id="simpleDetailsTable"[^>]*>(.*?)</table>',
            html,
            re.DOTALL,
        )
        if not table_match:
            raise ServiceError(
                "Oxford planning application summary is missing case details",
                status_code=502,
            )

        fields: dict[str, str] = {}
        for label, value in re.findall(
            r"<tr>\s*<th[^>]*>(.*?)</th>\s*<td>(.*?)</td>\s*</tr>",
            table_match.group(1),
            re.DOTALL,
        ):
            clean_label = cls._clean_html_text(label)
            clean_value = cls._clean_html_text(value)
            if clean_label:
                fields[clean_label] = clean_value

        reference = fields.get("Reference")
        address = fields.get("Address")
        proposal = fields.get("Proposal")
        if not (reference and address and proposal):
            raise ServiceError(
                "Oxford planning application summary is missing expected fields",
                detail={"fields": fields},
                status_code=502,
            )

        summary_link_match = re.search(
            r'<a href="([^"]+)" id="subtab_summary" class="active">',
            html,
        )
        resolved_detail_url = (
            urljoin(cls.base_url, unescape(summary_link_match.group(1)))
            if summary_link_match
            else detail_url
        )

        return PlanningApplicationSummary(
            application_id=reference,
            location=address,
            ward=default_ward,
            summary=proposal,
            detail_url=resolved_detail_url,
        )

    @staticmethod
    def _clean_html_text(value: str) -> str:
        """Strip tags, normalize whitespace, and unescape HTML text."""
        without_tags = re.sub(r"<[^>]+>", " ", value)
        return re.sub(r"\s+", " ", unescape(without_tags)).strip()


def get_planning_service() -> PlanningService:
    """Create a planning service instance."""
    return PlanningService()
