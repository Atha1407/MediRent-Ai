"""FastAPI Router for Smart Equipment Allocation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.schemas.allocation import (
    AllocationMetadataResponse,
    AllocationRecommendationResponse,
    AllocationRequest,
)
from backend.services.allocation_service import (
    AllocationService,
    get_allocation_service,
)

router = APIRouter(
    prefix="/api/allocation",
    tags=["Smart Equipment Allocation"],
)


@router.post(
    "/recommend",
    response_model=AllocationRecommendationResponse,
    summary="Generate optimal smart equipment allocation recommendation",
    description=(
        "Evaluates candidate physical equipment units against the 4 hard constraints "
        "(correct equipment type, currently not rented, no overlapping bookings, and no "
        "maintenance conflicts) and applies the authoritative 7-factor suitability scoring "
        "policy (Availability, Condition, Maintenance, Window, Duration Fit, Current Utilisation, "
        "and Future Demand) to recommend the optimal unit."
    ),
)
async def recommend_equipment(
    request: AllocationRequest,
    service: AllocationService = Depends(get_allocation_service),
) -> AllocationRecommendationResponse:
    """Recommend the optimal equipment unit for a customer rental request."""
    try:
        return service.recommend_equipment(request)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            ) from exc


@router.get(
    "",
    response_model=AllocationMetadataResponse,
    summary="Get smart allocation operational metadata and scoring weights",
    description=(
        "Returns system operational status, total catalogued physical units, total "
        "equipment categories tracked, and the transparent 7-factor scoring weights."
    ),
)
async def get_allocation_metadata(
    service: AllocationService = Depends(get_allocation_service),
) -> AllocationMetadataResponse:
    """Retrieve smart equipment allocation system configuration and metadata."""
    return service.get_metadata()
