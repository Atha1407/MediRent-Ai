"""FastAPI Router for Equipment Utilisation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.schemas.utilisation import (
    AvailabilitySnapshotResponse,
    CategoryUtilisationResponse,
    EquipmentUtilisationDetailResponse,
    OverallUtilisationResponse,
)
from backend.services.utilisation_service import (
    UtilisationService,
    get_utilisation_service,
)

router = APIRouter(
    prefix="/api/utilisation",
    tags=["Equipment Utilisation"],
)


@router.get(
    "",
    response_model=OverallUtilisationResponse,
    summary="Get overall equipment utilisation dashboard",
    description=(
        "Returns overall pool-level utilisation metrics across all 16 medical equipment "
        "types, data-driven quartile thresholds (25th and 75th percentiles), total inventory "
        "counts, currently rented and available units, and individual equipment utilisation items."
    ),
)
async def get_overall_utilisation(
    service: UtilisationService = Depends(get_utilisation_service),
) -> OverallUtilisationResponse:
    """Retrieve aggregate equipment utilisation and individual summaries."""
    return service.get_overall_utilisation()


@router.get(
    "/category",
    response_model=CategoryUtilisationResponse,
    summary="Get category-wise equipment utilisation ranking",
    description=(
        "Returns aggregate utilisation metrics and ranking across all 7 equipment categories, "
        "sorted from highest to lowest utilisation percentage."
    ),
)
async def get_category_utilisation(
    service: UtilisationService = Depends(get_utilisation_service),
) -> CategoryUtilisationResponse:
    """Retrieve category-wise equipment utilisation breakdown and ranking."""
    return service.get_category_utilisation()


@router.get(
    "/availability",
    response_model=AvailabilitySnapshotResponse,
    summary="Get current warehouse equipment availability snapshot",
    description=(
        "Returns current snapshot of inventory availability across all 16 equipment types "
        "as of the reference snapshot date (2026-07-31), showing active rentals and units "
        "currently available for immediate deployment."
    ),
)
async def get_availability_snapshot(
    service: UtilisationService = Depends(get_utilisation_service),
) -> AvailabilitySnapshotResponse:
    """Retrieve warehouse inventory availability snapshot."""
    return service.get_availability_snapshot()


@router.get(
    "/equipment/{equipment_name}",
    response_model=EquipmentUtilisationDetailResponse,
    summary="Get detailed utilisation metrics for a specific equipment",
    description=(
        "Returns comprehensive utilisation metrics for a specific medical equipment type, "
        "including analysis period, total inventory, planned rental days, available equipment "
        "days, utilisation percentage, quartile status, current availability, and actionable insight."
    ),
)
async def get_equipment_utilisation_detail(
    equipment_name: str,
    service: UtilisationService = Depends(get_utilisation_service),
) -> EquipmentUtilisationDetailResponse:
    """Retrieve detailed utilisation metrics for a specific medical equipment."""
    detail = service.get_equipment_utilisation(equipment_name)
    if detail is None:
        valid_items = sorted(service.get_equipment_names())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Equipment '{equipment_name}' not found. "
                f"Available equipment: {valid_items}"
            ),
        )
    return detail
