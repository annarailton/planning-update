"""Planning application endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from schemas.planning import (
    PlanningApplicationDateType,
    PlanningApplicationSearchResponse,
)
from services.planning_service import PlanningService, get_planning_service

router = APIRouter(tags=["Planning"])

PlanningServiceDep = Annotated[PlanningService, Depends(get_planning_service)]


@router.get(
    "/planning-applications",
    response_model=PlanningApplicationSearchResponse,
    summary="Get weekly planning applications from Oxford City Council",
)
async def get_planning_applications(
    planning_service: PlanningServiceDep,
    ward: str | None = Query(
        default=None,
        description="Ward name or code. Example: Hinksey Park or HINKPK",
    ),
    week_beginning: str | None = Query(
        default=None,
        description="Week beginning label from Oxford's weekly list. Defaults to the latest available week.",
    ),
    date_type: PlanningApplicationDateType = Query(
        default=PlanningApplicationDateType.VALIDATED,
        description="Whether to search applications validated or decided in the selected week.",
    ),
) -> PlanningApplicationSearchResponse:
    """Return normalized weekly planning applications."""
    return await planning_service.get_weekly_applications(
        ward=ward,
        week_beginning=week_beginning,
        date_type=date_type,
    )
