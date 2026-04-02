"""Schemas for planning application search results."""

from enum import Enum

from pydantic import Field

from .base import CamelCaseModel


class PlanningApplicationDateType(str, Enum):
    """Supported Oxford planning weekly list date filters."""

    VALIDATED = "validated"
    DECIDED = "decided"


class PlanningFilterOption(CamelCaseModel):
    """Selectable filter option from the source site."""

    value: str = Field(..., description="Raw source value")
    label: str = Field(..., description="Display label")


class PlanningApplicationSummary(CamelCaseModel):
    """Normalized planning application summary."""

    application_id: str = Field(..., description="Council application reference")
    location: str = Field(..., description="Application address or location")
    ward: str | None = Field(default=None, description="Ward name when available")
    summary: str = Field(..., description="Short application summary")
    detail_url: str = Field(..., description="Source URL for the application")


class PlanningApplicationFilters(CamelCaseModel):
    """Filters applied to the current response."""

    ward: str | None = Field(default=None, description="Resolved ward label")
    week_beginning: str = Field(..., description="Week beginning label from Oxford")
    date_type: PlanningApplicationDateType = Field(
        ..., description="Whether validated or decided applications were fetched"
    )


class PlanningApplicationAvailableFilters(CamelCaseModel):
    """Available filters discovered from the source form."""

    wards: list[PlanningFilterOption] = Field(
        default_factory=list, description="Ward options advertised by the source"
    )
    weeks: list[str] = Field(
        default_factory=list, description="Available week-beginning values"
    )


class PlanningApplicationSearchResponse(CamelCaseModel):
    """Response for planning application searches."""

    applications: list[PlanningApplicationSummary] = Field(default_factory=list)
    total_count: int = Field(..., description="Number of applications returned")
    filters: PlanningApplicationFilters
    available_filters: PlanningApplicationAvailableFilters
