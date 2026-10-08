"""Pydantic schemas for the Revenue Prediction module."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ForecastPeriod(BaseModel):
    """Represents a future forecasting timeframe."""

    year: int = Field(..., description="Target forecast year", json_schema_extra={"example": 2026})
    month: int = Field(..., description="Target forecast month number (1-12)", json_schema_extra={"example": 8})
    label: str = Field(..., description="Human-readable forecast label", json_schema_extra={"example": "August 2026"})


class HistoricalPeriod(BaseModel):
    """Represents the most recent historical observation timeframe."""

    year: int = Field(..., description="Year of the latest historical observation", json_schema_extra={"example": 2026})
    month: int = Field(..., description="Month number of the latest historical observation", json_schema_extra={"example": 7})
    label: str = Field(..., description="Human-readable historical label", json_schema_extra={"example": "July 2026"})


class RevenueModelMetrics(BaseModel):
    """Validation performance metrics for the evaluated revenue model."""

    model_name: str = Field(..., description="Name of the selected forecasting model", json_schema_extra={"example": "Demand-Based Revenue Forecasting"})
    mae: float = Field(..., description="Mean Absolute Error in INR on test set", json_schema_extra={"example": 142622.32})
    rmse: float = Field(..., description="Root Mean Squared Error in INR on test set", json_schema_extra={"example": 172030.31})
    r2: float = Field(..., description="R-squared coefficient of determination", json_schema_extra={"example": 0.3740})
    test_period: str = Field(..., description="Validation test period", json_schema_extra={"example": "December 2025 - July 2026"})
    methodology: str = Field(..., description="Mathematical formulation of the pipeline", json_schema_extra={"example": "Expected Revenue = Expected Rental Volume × Historical Average Revenue per Rental"})
    avg_revenue_per_rental: float = Field(..., description="Historical average revenue per rental in INR", json_schema_extra={"example": 4186.80})


class HistoricalRevenueRecord(BaseModel):
    """Monthly historical validation record comparing actual vs predicted revenue."""

    year: int = Field(..., description="Observation year", json_schema_extra={"example": 2026})
    month: int = Field(..., description="Observation month number (1-12)", json_schema_extra={"example": 7})
    year_month: str = Field(..., description="Formatted year-month identifier", json_schema_extra={"example": "2026-07"})
    monthly_revenue: float = Field(..., description="Actual recorded monthly revenue in INR", json_schema_extra={"example": 989370.0})
    predicted_revenue: Optional[float] = Field(None, description="Demand-based predicted revenue in INR", json_schema_extra={"example": 820613.32})
    error: Optional[float] = Field(None, description="Residual error: Actual - Predicted", json_schema_extra={"example": 168756.68})
    absolute_error: Optional[float] = Field(None, description="Absolute error: |Actual - Predicted|", json_schema_extra={"example": 168756.68})


class RevenueSummaryStatistics(BaseModel):
    """Summary statistics for historical monthly revenue time series."""

    total_historical_months: int = Field(..., description="Total historical monthly observations available", json_schema_extra={"example": 31})
    average_monthly_revenue: float = Field(..., description="Historical average monthly revenue in INR", json_schema_extra={"example": 483321.45})
    min_monthly_revenue: float = Field(..., description="Minimum recorded monthly revenue in INR", json_schema_extra={"example": 285690.0})
    max_monthly_revenue: float = Field(..., description="Maximum recorded monthly revenue in INR", json_schema_extra={"example": 989370.0})
    total_historical_revenue: float = Field(..., description="Cumulative total historical revenue in INR", json_schema_extra={"example": 14982965.0})


class RevenueOverviewResponse(BaseModel):
    """Overview response for the Revenue Prediction module."""

    forecast_period: ForecastPeriod
    latest_historical_period: HistoricalPeriod
    latest_historical_revenue: float = Field(..., description="Most recent recorded actual monthly revenue (July 2026)", json_schema_extra={"example": 989370.0})
    predicted_revenue: float = Field(..., description="Predicted rental revenue for the upcoming month (August 2026)", json_schema_extra={"example": 988085.43})
    expected_rental_volume: float = Field(..., description="Expected rental volume derived from Demand baseline", json_schema_extra={"example": 236.0})
    avg_revenue_per_rental: float = Field(..., description="Training period average revenue per rental in INR", json_schema_extra={"example": 4186.80})
    insight: str = Field(..., description="Actionable business interpretation of the revenue forecast", json_schema_extra={"example": "Expected revenue for August 2026 is ₹988,085.43 based on 236 predicted rentals at ₹4,186.80 average revenue per rental."})
    model_metrics: RevenueModelMetrics
    summary_statistics: RevenueSummaryStatistics
    recent_test_records: List[HistoricalRevenueRecord]


class MonthlyRevenueRecord(BaseModel):
    """Monthly timeline data point showing historical actuals and demand-based forecasts."""

    year: int = Field(..., description="Year", json_schema_extra={"example": 2026})
    month: int = Field(..., description="Month number (1-12)", json_schema_extra={"example": 8})
    year_month: str = Field(..., description="Formatted year-month identifier", json_schema_extra={"example": "2026-08"})
    historical_revenue: Optional[float] = Field(None, description="Actual recorded monthly revenue in INR (null for future forecast)", json_schema_extra={"example": 989370.0})
    predicted_revenue: Optional[float] = Field(None, description="Predicted revenue in INR (null if outside test/forecast window)", json_schema_extra={"example": 988085.43})
    error: Optional[float] = Field(None, description="Residual error (Actual - Predicted) where both exist", json_schema_extra={"example": 168756.68})
    absolute_error: Optional[float] = Field(None, description="Absolute error |Actual - Predicted| where both exist", json_schema_extra={"example": 168756.68})
    is_forecast: bool = Field(False, description="Flag indicating if this record represents a future forecast period", json_schema_extra={"example": False})


class MonthlyRevenueResponse(BaseModel):
    """Chronological monthly revenue timeline."""

    forecast_period: ForecastPeriod
    filter_year: Optional[int] = Field(None, description="Year filter applied, if any", json_schema_extra={"example": 2026})
    total_periods: int = Field(..., description="Number of timeline data points returned", json_schema_extra={"example": 32})
    timeline: List[MonthlyRevenueRecord]


class RevenueModelComparisonItem(BaseModel):
    """Validation performance benchmark for an evaluated revenue model."""

    model: str = Field(..., description="Name of the evaluated model", json_schema_extra={"example": "Demand-Based Revenue"})
    mae: float = Field(..., description="Mean Absolute Error in INR", json_schema_extra={"example": 142622.32})
    rmse: float = Field(..., description="Root Mean Squared Error in INR", json_schema_extra={"example": 172030.31})
    r2: Optional[float] = Field(None, description="R-squared metric (may be negative for underperforming regressors)", json_schema_extra={"example": 0.3740})


class RevenueModelComparisonResponse(BaseModel):
    """Comparison of revenue forecasting models evaluated during the ML phase."""

    selected_model: str = Field(..., description="The chosen model deployed for production forecasting", json_schema_extra={"example": "Demand-Based Revenue"})
    rationale: str = Field(..., description="Justification for selecting the model per PRD", json_schema_extra={"example": "Demand-Based Revenue Forecasting achieved lowest MAE and RMSE with highest R²."})
    models: List[RevenueModelComparisonItem]
