"""Data models for the planning application scraper."""

import re
from datetime import date, datetime
from typing import ClassVar, Literal

from pint import UndefinedUnitError, UnitRegistry
from pydantic import BaseModel, Field, field_validator, model_validator

from .lookup.location_lookup import (
    PARISH_CODE_TO_NAME,
    WARD_CODE_TO_NAME,
    resolve_parish_code,
    resolve_ward_code,
)

ApplicationStatusMode = Literal["validated", "decided"]
CliStatusMode = Literal["validated", "decided", "both"]
# Oxford planning references use a two-digit year, a five-digit sequence, and a
# short uppercase suffix such as FUL or LBC, all separated by forward slashes,
# for example "26/00281/FUL"
APPLICATION_ID_RE = re.compile(r"\b\d{2}/\d{5}/[A-Z0-9]+\b")
# Capture a likely UK postcode in either spaced or compact form so we can pull
# it back out of the free-text planning-application address field.#
# We need this for ward / parish lookups later
#
# The pattern allows:
# - one or two leading letters
# - one digit
# - an optional outward-code suffix character (this is a real postcode thing - look it up!)
# - optional whitespace
# - one digit plus two trailing letters
#
# That covers common postcode shapes such as `OX1 4RP`, `OX14RP`, and `W1A 0AX`.
UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
    re.IGNORECASE,
)
# We use this to require string distances to start with an explicit numeric
# value so inputs like "miles" are rejected instead of being interpreted by
# pint as 1 mile.
#
# Match a leading signed or unsigned decimal number:
# - optional `+` or `-`
# - digits with an optional fractional part, such as `1` or `1.5`
# - or a leading-decimal form such as `.5`
LEADING_NUMBER_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)")
UNIT_REGISTRY = UnitRegistry()


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

    UK_POSTCODE_RE: ClassVar[re.Pattern[str]] = UK_POSTCODE_RE

    application_ref: ApplicationRef
    proposal: str
    url: str
    address: str
    postcode: str | None = None
    received: date
    validated: date
    # These are found from the application page itself
    # Not all of these will exist (e.g. "Decision" only appears when there's a decision)
    ward: str | None = None
    parish: str | None = None
    decided: date | None = None
    consultation_deadline: date | None = None
    determination_deadline: date | None = None
    status: str | None = None
    decision: str | None = None
    keyword_matches: list[str] | None = None
    is_major_application: bool = False
    inclusion_reason: str | None = None

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

        Supported input formats:
        - Oxford site strings like ``Thu 12 Mar 2026`` from scraped HTML
        - ISO strings like ``2026-03-12`` from cached JSON
        - Existing ``date`` objects from internal model updates
        """
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if not v.strip():
            raise ValueError("Required application date cannot be empty")
        try:
            # Oxford site format, for example "Thu 12 Mar 2026".
            return datetime.strptime(v, "%a %d %b %Y").date()
        except ValueError:
            return date.fromisoformat(v)

    @model_validator(mode="after")
    def populate_postcode_from_address(self) -> "Application":
        """Populate the derived postcode field from the address."""
        self.postcode = self.postcode_from_address(self.address)
        return self

    @classmethod
    def postcode_from_address(cls, address: str) -> str | None:
        """Extract a normalized UK postcode from an address string.

        Returns the postcode in standard uppercase form with a single space
        before the final three characters, or ``None`` if the address does not
        contain a recognizable postcode.
        """
        match = cls.UK_POSTCODE_RE.search(address)
        if match is None:
            return None

        compact_postcode = re.sub(r"\s+", "", match.group(1)).upper()
        return f"{compact_postcode[:-3]} {compact_postcode[-3:]}"


class CommitteeApplication(BaseModel):
    """A planning application listed on an upcoming committee agenda."""

    application_ref: ApplicationRef
    committee_date: date
    proposal: str
    address: str
    agenda_url: str
    report_url: str
    recommendation: str | None = None

    @field_validator("committee_date", mode="before")
    @classmethod
    def validate_committee_date(cls, v: str | date) -> date:
        """Validate and parse committee meeting dates."""
        if isinstance(v, date):
            return v
        if not v.strip():
            raise ValueError("Committee date cannot be empty")
        try:
            return datetime.strptime(v, "%d %b %Y").date()
        except ValueError:
            return date.fromisoformat(v)


class CommitteeSection(BaseModel):
    """Coming to next planning committee applications for rendered output."""

    title: str = "Coming to next planning committee"
    applications: list[CommitteeApplication]


class PlanningQuery(BaseModel):
    """User-facing query options for the weekly list search.

    Input to the scraper.
    """

    ward_name: str | None = None
    parish_name: str | None = None
    requested_week: str | None = None
    distance_around_ward_meters: float = 0.0
    distance_around_parish_meters: float = 0.0
    distance_around_ward_label: str | None = None
    distance_around_parish_label: str | None = None
    keywords: list[str] = Field(default_factory=list)
    major: bool = False
    status_mode: ApplicationStatusMode = "validated"

    def uses_keyword_matching(self) -> bool:
        """Return whether this query should apply proposal keyword matching."""
        return bool(self.keywords)

    def uses_major_matching(self) -> bool:
        """Return whether this query should filter to current major applications."""
        return self.major

    def uses_distance_around_ward(self) -> bool:
        """Return whether this query should include a ward-distance buffer."""
        return self.distance_around_ward_meters > 0

    def uses_distance_around_parish(self) -> bool:
        """Return whether this query should include a parish-distance buffer."""
        return self.distance_around_parish_meters > 0

    def resolve_ward_code(self) -> str:
        """Resolve the configured ward name to an Oxford ward code.

        Returns:
            The resolved ward code, or an empty string for all wards.
        """
        if self.uses_keyword_matching() or self.uses_major_matching():
            return ""
        # This is because distance-based queries need the full results to check distances against
        # so they can't be pre-filtered by ward/parish.
        if self.uses_distance_around_ward():
            return ""
        if self.ward_name is None:
            return ""
        return resolve_ward_code(self.ward_name)

    def resolve_parish_code(self) -> str:
        """Resolve the configured parish name to an Oxford parish code.

        Returns:
            The resolved parish code, or an empty string for all parishes.
        """
        if self.uses_keyword_matching() or self.uses_major_matching():
            return ""
        # This is because distance-based queries need the full results to check distances against
        # so they can't be pre-filtered by ward/parish.
        if self.uses_distance_around_parish():
            return ""
        if self.parish_name is None:
            return ""
        return resolve_parish_code(self.parish_name)

    def resolved_ward_name(self) -> str:
        """Return the canonical human-readable ward name for the query.

        Returns:
            The canonical ward name, or ``All wards`` when no ward is set.
        """
        if self.ward_name is None:
            return "All wards"
        ward_code = resolve_ward_code(self.ward_name)
        return WARD_CODE_TO_NAME[ward_code]

    def resolved_parish_name(self) -> str:
        """Return the canonical human-readable parish name for the query.

        Returns:
            The canonical parish name, or ``All parishes`` when no parish is set.
        """
        if self.parish_name is None:
            return "All parishes"
        parish_code = resolve_parish_code(self.parish_name)
        return PARISH_CODE_TO_NAME[parish_code]

    def matching_keywords(self, proposal: str) -> list[str]:
        """Return the configured lowercase keywords found in a proposal."""
        proposal_text = proposal.lower()
        return [keyword for keyword in self.keywords if keyword in proposal_text]

    def selected_week(self, available_weeks: list[str]) -> str:
        """Return the week value this query should use.

        Args:
            available_weeks: Week labels available from the weekly-list form.

        Returns:
            The selected week label to query.
        """
        if self.requested_week is not None:
            return self.requested_week
        return available_weeks[0]

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


class CliConfig(BaseModel):
    """Optional CLI defaults loaded from TOML."""

    LEADING_NUMBER_RE: ClassVar[re.Pattern[str]] = LEADING_NUMBER_RE
    UNIT_REGISTRY: ClassVar[UnitRegistry] = UNIT_REGISTRY

    debug: bool | None = None
    ward: str | list[str] | None = None
    parish: str | None = None
    status_mode: CliStatusMode | None = None
    week: str | None = None
    keywords: str | list[str] | None = None
    major: bool | None = None
    distance_around_ward: float = 0.0
    distance_around_parish: float = 0.0
    distance_around_ward_label: str | None = None
    distance_around_parish_label: str | None = None
    email_to: str | None = None

    @staticmethod
    def normalize_distance_label(value: str) -> str:
        """Collapse spacing in a distance string for stable display."""
        return " ".join(value.split())

    @classmethod
    def parse_distance_around_X(cls, value: str | int | float | None) -> float:
        """Parse a distance-around-ward or distance-around-parish config value into meters."""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            if value == 0:
                return 0.0
            raise TypeError(
                "distance_around_ward/parish must include units such as '0.25 miles' or '0.4 km'"
            )
        if not isinstance(value, str):
            raise TypeError(
                "distance_around_ward/parish must be provided as a string or zero"
            )

        raw_value = value.strip()
        if not raw_value:
            return 0.0
        # Pint will happily parse bare units like "miles" as 1 mile, but for
        # config we want users to provide an explicit quantity up front.
        if cls.LEADING_NUMBER_RE.match(raw_value) is None:
            raise ValueError(
                "distance_around_ward/parish must be a valid distance such as '0.25 miles' or '0.4 km'"
            )

        try:
            quantity = cls.UNIT_REGISTRY(raw_value)
        except (UndefinedUnitError, TypeError) as exc:
            raise ValueError(
                "distance_around_ward/parish must be a valid distance such as '0.25 miles' or '0.4 km'"
            ) from exc

        if getattr(quantity, "magnitude", None) == 0:
            return 0.0
        if not hasattr(quantity, "to"):
            raise ValueError(
                "distance_around_ward/parish must include length units such as miles or km"
            )

        try:
            return float(quantity.to("meter").magnitude)
        except Exception as exc:  # pragma: no cover
            raise ValueError(
                "distance_around_ward/parish must include length units such as miles or km"
            ) from exc

    @field_validator("distance_around_ward", mode="before")
    @classmethod
    def validate_distance_around_ward(cls, value: str | int | float | None) -> float:
        """Normalize distance-around-ward config values into meters."""
        return cls.parse_distance_around_X(value)

    @field_validator("distance_around_parish", mode="before")
    @classmethod
    def validate_distance_around_parish(cls, value: str | int | float | None) -> float:
        """Normalize distance-around-parish config values into meters."""
        return cls.parse_distance_around_X(value)

    @model_validator(mode="before")
    @classmethod
    def populate_distance_labels(cls, data: object) -> object:
        """Preserve raw distance strings for result-card display."""
        if not isinstance(data, dict):
            return data

        normalized_data = dict(data)
        ward_distance = normalized_data.get("distance_around_ward")
        if isinstance(ward_distance, str) and ward_distance.strip():
            normalized_data["distance_around_ward_label"] = (
                cls.normalize_distance_label(ward_distance)
            )

        parish_distance = normalized_data.get("distance_around_parish")
        if isinstance(parish_distance, str) and parish_distance.strip():
            normalized_data["distance_around_parish_label"] = (
                cls.normalize_distance_label(parish_distance)
            )

        return normalized_data

    @model_validator(mode="after")
    def clear_zero_distance_labels(self) -> "CliConfig":
        """Drop display labels when the parsed distance is zero."""
        if self.distance_around_ward == 0:
            self.distance_around_ward_label = None
        if self.distance_around_parish == 0:
            self.distance_around_parish_label = None
        return self


class CliInputs(BaseModel):
    """Raw CLI inputs before config defaults are applied."""

    debug: bool = False
    ward: str | list[str] | None = None
    parish: str | None = None
    status: CliStatusMode | None = None
    week: str | None = None
    keywords: str | list[str] | None = None
    major: bool | None = None
    email_to: str | None = None


class ResolvedCliOptions(BaseModel):
    """Fully resolved runtime options derived from CLI inputs and config."""

    debug: bool = False
    email_recipient: str | None = None
    status_mode: CliStatusMode = "validated"
    queries: list[PlanningQuery]


class ApplicationSection(BaseModel):
    """A named section of applications for rendered output."""

    title: str
    applications: list[Application]
    major_apps_notice_message: str | None = (
        None  # This holds whether to show the "no major applications" notice
    )
    empty_state_message: str = "No applications"


class PlanningReport(BaseModel):
    """Aggregated applications and sections ready for rendering."""

    applications: list[Application]
    sections: list[ApplicationSection]
    actual_week: str | None = None
    committee_section: CommitteeSection | None = None
