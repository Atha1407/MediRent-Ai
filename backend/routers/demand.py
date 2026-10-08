"""FastAPI Router for Demand Prediction endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.schemas.demand import (
    DemandOverviewResponse,
    EquipmentDemandDetailResponse,
    EquipmentInfo,
    ModelComparisonResponse,
    MonthlyDemandResponse,
)
from backend.services.demand_service import DemandService, get_demand_service

router = APIRouter(
    prefix="/api/demand",
    tags=["Demand Prediction"],
)


@router.get(
    "",
    response_model=DemandOverviewResponse,
    summary="Get demand forecast overview across all medical equipment",
    description=(
        "Returns the aggregate next-month demand forecast across all 16 medical equipment types "
        "using the finalized Previous-Month Demand Baseline model. Includes model evaluation "
        "metrics, total predicted rental volume, and per-equipment demand predictions with "
        "trend momentum classification and actionable insights."
    ),
)
async def get_demand_overview(
    service: DemandService = Depends(get_demand_service),
) -> DemandOverviewResponse:
    """Retrieve overall demand prediction for the upcoming month."""
    return service.get_demand_overview()


@router.get(
    "/monthly",
    response_model=MonthlyDemandResponse,
    summary="Get monthly demand timeline and next-month forecast",
    description=(
        "Returns monthly demand timeline (historical actuals vs lag-1 baseline predictions) "
        "spanning from January 2024 to July 2026, plus the next-month forecast (August 2026). "
        "Can optionally be filtered by equipment name or equipment category."
    ),
)
async def get_monthly_demand(
    equipment: Optional[str] = Query(
        None,
        description="Filter monthly timeline by specific equipment name (e.g., 'Oxygen Concentrator')",
    ),
    category: Optional[str] = Query(
        None,
        description="Filter monthly timeline by equipment category (e.g., 'Respiratory Equipment')",
    ),
    service: DemandService = Depends(get_demand_service),
) -> MonthlyDemandResponse:
    """Retrieve monthly demand history and upcoming forecast."""
    try:
        return service.get_monthly_demand(equipment=equipment, category=category)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/comparison",
    response_model=ModelComparisonResponse,
    summary="Get demand model evaluation comparison benchmarks",
    description=(
        "Returns validation performance metrics (MAE, RMSE, R²) for all models evaluated "
        "during the ML development phase as documented in the PRD (Previous-Month Baseline, "
        "Ridge Regression, Ridge - Demand Change)."
    ),
)
async def get_model_comparison(
    service: DemandService = Depends(get_demand_service),
) -> ModelComparisonResponse:
    """Retrieve ML model evaluation comparison benchmarks."""
    return service.get_model_comparison()


@router.get(
    "/equipments",
    response_model=List[EquipmentInfo],
    summary="List all tracked medical equipment items",
    description="Returns all 16 tracked medical equipment types and their assigned categories.",
)
async def list_equipments(
    service: DemandService = Depends(get_demand_service),
) -> List[EquipmentInfo]:
    """Retrieve list of all medical equipment items."""
    return service.get_equipment_list()


@router.get(
    "/equipment/{equipment_name}",
    response_model=EquipmentDemandDetailResponse,
    summary="Get detailed demand forecast and history for an equipment",
    description=(
        "Returns comprehensive demand intelligence for a specific medical equipment, "
        "including complete 31-month historical timeline with prediction errors, "
        "time-aware test-set MAE, historical summary statistics, next-month forecast, "
        "and momentum trend classification."
    ),
)
async def get_equipment_demand_detail(
    equipment_name: str,
    service: DemandService = Depends(get_demand_service),
) -> EquipmentDemandDetailResponse:
    """Retrieve detailed demand forecast and historical timeline for a specific equipment."""
    detail = service.get_equipment_demand_detail(equipment_name)
    if detail is None:
        valid_items = sorted([item.equipment for item in service.get_equipment_list()])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Equipment '{equipment_name}' not found. "
                f"Available equipment: {valid_items}"
            ),
        )
    return detail
