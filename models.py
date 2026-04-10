"""Data models for the planning application scraper."""

import re
from datetime import date, datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, field_validator

from location_lookup import (
    PARISH_CODE_TO_NAME,
    WARD_CODE_TO_NAME,
    resolve_parish_code,
    resolve_ward_code,
)

ApplicationStatusMode = Literal["validated", "decided"]
APPLICATION_ID_RE = re.compile(r"\b\d{2}/\d{5}/[A-Z0-9]+\b")


class ApplicationRef(BaseModel):
    """A validated planning application reference."""

    value: str
    APPLICATION_ID_RE: ClassVar[re.Pattern[str]] = APPLICATION_ID_RE

    @field_validator("value")
    @classmethod
    def validate_application_id(cls, v: str) -> str:
        """Validate that the reference matches the expected format.

        Args:
            v: Raw application reference value to validate.

        Returns:
            The validated application reference.
        """
        if not cls.APPLICATION_ID_RE.fullmatch(v):
            raise ValueError(f"Invalid application reference: {v}")
        return v


class Application(BaseModel):
    """A planning application scraped from the weekly list.

    ``status`` and ``decision`` are kept as plain strings because these values
    come directly from the Oxford site in the human-readable form we want to
    return, so extra model layers or strict enum-style validation add more
    complexity than value.
    """

    application_ref: ApplicationRef
    proposal: str
    url: str
    address: str
    received: date
    validated: date
    decided: date | None = None
    consultation_deadline: date | None = None
    determination_deadline: date | None = None
    status: str | None = None
    decision: str | None = None

    @field_validator(
        "received",
        "validated",
        "decided",
        "consultation_deadline",
        "determination_deadline",
        mode="before",
    )
    @classmethod
    def validate_application_date(cls, v: str | date | None) -> date | None:
        """Validate and parse application dates.

        Args:
            v: Raw date value to validate and parse.

        Returns:
            The validated application date, or ``None`` for empty optional values.
        """
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if not v.strip():
            raise ValueError("Required application date cannot be empty")
        return datetime.strptime(v, "%a %d %b %Y").date()


class PlanningQuery(BaseModel):
    """User-facing query options for the weekly list search.

    Input to the scraper.
    """

    ward_name: str | None = None
    parish_name: str | None = None
    requested_week: str | None = None
    fallback_weeks: int = 1
    strict: bool = False
    status_mode: ApplicationStatusMode = "validated"

    def resolve_ward_code(self) -> str:
        """Resolve the configured ward name to an Oxford ward code.

        Returns:
            The resolved ward code, or an empty string for all wards.
        """
        if self.ward_name is None:
            return ""
        return resolve_ward_code(self.ward_name)

    def resolve_parish_code(self) -> str:
        """Resolve the configured parish name to an Oxford parish code.

        Returns:
            The resolved parish code, or an empty string for all parishes.
        """
        if self.parish_name is None:
            return ""
        return resolve_parish_code(self.parish_name)

    def resolved_ward_name(self) -> str:
        """Return the canonical human-readable ward name for the query.

        Returns:
            The canonical ward name, or ``All wards`` when no ward is set.
        """
        ward_code = self.resolve_ward_code()
        if not ward_code:
            return "All wards"
        return WARD_CODE_TO_NAME[ward_code]

    def resolved_parish_name(self) -> str:
        """Return the canonical human-readable parish name for the query.

        Returns:
            The canonical parish name, or ``All parishes`` when no parish is set.
        """
        parish_code = self.resolve_parish_code()
        if not parish_code:
            return "All parishes"
        return PARISH_CODE_TO_NAME[parish_code]

    def candidate_weeks(self, available_weeks: list[str]) -> list[str]:
        """Return the ordered week values this query should try.

        Args:
            available_weeks: Week labels available from the weekly-list form.

        Returns:
            The ordered week labels to query.
        """
        if self.requested_week is not None:
            return [self.requested_week]
        return available_weeks[: max(1, self.fallback_weeks + 1)]

    def build_search_payload(self, *, csrf_token: str, week: str) -> dict[str, str]:
        """Build the weekly-list form payload for a single query attempt.

        Args:
            csrf_token: CSRF token extracted from the weekly-list form.
            week: Exact week label from the weekly-list dropdown.

        Returns:
            Form payload for a single weekly-list request.
        """
        return {
            "_csrf": csrf_token,
            "searchCriteria.parish": self.resolve_parish_code(),
            "searchCriteria.ward": self.resolve_ward_code(),
            "week": week,
            "dateType": (
                "DC_Decided" if self.status_mode == "decided" else "DC_Validated"
            ),
            "searchType": "Application",
        }
