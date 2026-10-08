"""FastAPI Router for Revenue Prediction endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.schemas.revenue import (
    MonthlyRevenueResponse,
    RevenueModelComparisonResponse,
    RevenueOverviewResponse,
)
from backend.services.revenue_service import RevenueService, get_revenue_service

router = APIRouter(
    prefix="/api/revenue",
    tags=["Revenue Prediction"],
)


@router.get(
    "",
    response_model=RevenueOverviewResponse,
    summary="Get revenue forecast overview for upcoming month",
    description=(
        "Returns next-month revenue forecast for August 2026 derived from the finalized "
        "Demand-Based Revenue Forecasting pipeline: Expected Revenue = Expected Rental Volume × "
        "Historical Average Revenue per Rental (₹4,186.80). Includes latest historical revenue "
        "(July 2026), validation metrics (MAE ₹142,622.32, RMSE ₹172,030.31, R² 0.3740), summary "
        "statistics, and historical validation records."
    ),
)
async def get_revenue_overview(
    service: RevenueService = Depends(get_revenue_service),
) -> RevenueOverviewResponse:
    """Retrieve overall revenue prediction and metrics for the upcoming month."""
    return service.get_revenue_overview()


@router.get(
    "/monthly",
    response_model=MonthlyRevenueResponse,
    summary="Get monthly revenue timeline and next-month forecast",
    description=(
        "Returns chronological monthly revenue timeline spanning 31 historical months "
        "(January 2024 to July 2026) with demand-based predictions and residuals where available, "
        "plus the upcoming forecast month (August 2026). Can optionally be filtered by year."
    ),
)
async def get_monthly_revenue(
    year: Optional[int] = Query(
        None,
        description="Filter monthly timeline by specific year (e.g., 2024, 2025, 2026)",
    ),
    service: RevenueService = Depends(get_revenue_service),
) -> MonthlyRevenueResponse:
    """Retrieve monthly revenue history and upcoming forecast."""
    try:
        return service.get_monthly_revenue(year=year)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/comparison",
    response_model=RevenueModelComparisonResponse,
    summary="Get revenue model evaluation comparison benchmarks",
    description=(
        "Returns validation performance metrics (MAE, RMSE, R²) for all models evaluated "
        "during the ML development phase as documented in the PRD (Demand-Based Revenue, "
        "Previous-Month Revenue, Random Forest, XGBoost, Ridge)."
    ),
)
async def get_model_comparison(
    service: RevenueService = Depends(get_revenue_service),
) -> RevenueModelComparisonResponse:
    """Retrieve ML revenue model evaluation comparison benchmarks."""
    return service.get_model_comparison()
