"""Data models for the planning application scraper."""

import re
from datetime import date, datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, field_validator

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
