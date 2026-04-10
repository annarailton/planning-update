"""Data models for the planning application scraper."""

import re
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
        """Validate that the reference matches the expected format."""
        if not cls.APPLICATION_ID_RE.fullmatch(v):
            raise ValueError(f"Invalid application reference: {v}")
        return v


class Application(BaseModel):
    """A planning application scraped from the weekly list."""

    application_ref: ApplicationRef
    proposal: str
    url: str
    week: str
