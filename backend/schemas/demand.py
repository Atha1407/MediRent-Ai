"""Pydantic schemas for the Demand Prediction module."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ForecastPeriod(BaseModel):
    """Represents a future forecasting timeframe."""

    year: int = Field(..., description="Target forecast year", json_schema_extra={"example": 2026})
    month: int = Field(..., description="Target forecast month number (1-12)", json_schema_extra={"example": 8})
    label: str = Field(..., description="Human-readable forecast label", json_schema_extra={"example": "August 2026"})


class ModelMetrics(BaseModel):
    """Evaluation metrics for the demand forecasting model."""

    model_name: str = Field(..., description="Name of the evaluated ML/baseline model", json_schema_extra={"example": "Previous-Month Demand Baseline"})
    mae: float = Field(..., description="Mean Absolute Error on the validation test set", json_schema_extra={"example": 4.5893})
    rmse: float = Field(..., description="Root Mean Squared Error on the validation test set", json_schema_extra={"example": 5.8858})
    r2: float = Field(..., description="R-squared coefficient of determination", json_schema_extra={"example": 0.4595})
    test_period: str = Field(..., description="Time-aware validation period", json_schema_extra={"example": "January 2026 - July 2026"})


class EquipmentDemandSummary(BaseModel):
    """Summary of demand prediction and momentum for an individual equipment item."""

    equipment: str = Field(..., description="Name of the medical equipment", json_schema_extra={"example": "Oxygen Concentrator"})
    category: str = Field(..., description="Equipment category classification", json_schema_extra={"example": "Respiratory Equipment"})
    latest_actual_demand: float = Field(..., description="Most recent actual monthly demand (July 2026)", json_schema_extra={"example": 17.0})
    predicted_demand: float = Field(..., description="Baseline forecast for the upcoming month (August 2026)", json_schema_extra={"example": 17.0})
    trend: str = Field(..., description="Momentum trend classification: increasing, decreasing, or stable", json_schema_extra={"example": "decreasing"})
    insight: str = Field(..., description="Actionable interpretation of the forecast", json_schema_extra={"example": "Demand for Oxygen Concentrator is expected to decrease based on recent monthly momentum."})


class DemandOverviewResponse(BaseModel):
    """Overall demand prediction response across all medical equipment."""

    forecast_period: ForecastPeriod
    total_predicted_demand: float = Field(..., description="Total aggregate predicted demand across all equipment for next month", json_schema_extra={"example": 236.0})
    equipment_count: int = Field(..., description="Total number of distinct equipment types tracked", json_schema_extra={"example": 16})
    model_metrics: ModelMetrics
    equipments: List[EquipmentDemandSummary]


class HistoricalDemandRecord(BaseModel):
    """Single monthly observation comparing actual demand against lag-1 baseline prediction."""

    year: int = Field(..., description="Observation year", json_schema_extra={"example": 2026})
    month: int = Field(..., description="Observation month number (1-12)", json_schema_extra={"example": 7})
    year_month: str = Field(..., description="Formatted year-month identifier", json_schema_extra={"example": "2026-07"})
    actual_demand: float = Field(..., description="Actual recorded rental count for this month", json_schema_extra={"example": 17.0})
    predicted_demand: Optional[float] = Field(None, description="Predicted rental count using previous-month baseline", json_schema_extra={"example": 27.0})
    residual_error: Optional[float] = Field(None, description="Actual demand minus predicted demand", json_schema_extra={"example": -10.0})
    absolute_error: Optional[float] = Field(None, description="Absolute error |Actual - Predicted|", json_schema_extra={"example": 10.0})
    trend_2m: Optional[float] = Field(None, description="Historical 2-month demand trend feature from dataset", json_schema_extra={"example": 4.0})


class HistoricalSummary(BaseModel):
    """Aggregate statistics for an equipment item's historical time series."""

    total_months: int = Field(..., description="Total historical monthly records", json_schema_extra={"example": 31})
    average_monthly_demand: float = Field(..., description="Historical average monthly demand", json_schema_extra={"example": 14.8})
    min_monthly_demand: float = Field(..., description="Minimum recorded monthly demand", json_schema_extra={"example": 4.0})
    max_monthly_demand: float = Field(..., description="Maximum recorded monthly demand", json_schema_extra={"example": 27.0})
    test_mae: Optional[float] = Field(None, description="MAE on 2026 test period for this equipment", json_schema_extra={"example": 5.43})


class EquipmentDemandDetailResponse(BaseModel):
    """Detailed historical and predicted demand response for a single equipment item."""

    equipment: str = Field(..., description="Name of the medical equipment", json_schema_extra={"example": "Oxygen Concentrator"})
    category: str = Field(..., description="Equipment category classification", json_schema_extra={"example": "Respiratory Equipment"})
    forecast_period: ForecastPeriod
    latest_actual_demand: float = Field(..., description="Most recent actual monthly demand", json_schema_extra={"example": 17.0})
    predicted_demand: float = Field(..., description="Baseline forecast for the upcoming month", json_schema_extra={"example": 17.0})
    trend: str = Field(..., description="Momentum trend classification: increasing, decreasing, or stable", json_schema_extra={"example": "decreasing"})
    insight: str = Field(..., description="Actionable interpretation of the forecast", json_schema_extra={"example": "Demand for Oxygen Concentrator is expected to decrease based on recent monthly momentum."})
    summary: HistoricalSummary
    history: List[HistoricalDemandRecord]


class MonthlyDemandRecord(BaseModel):
    """Aggregated demand data point for a specific month."""

    year: int = Field(..., description="Year", json_schema_extra={"example": 2026})
    month: int = Field(..., description="Month number (1-12)", json_schema_extra={"example": 8})
    year_month: str = Field(..., description="Formatted year-month identifier", json_schema_extra={"example": "2026-08"})
    total_actual_demand: Optional[float] = Field(None, description="Total actual rental demand across tracked equipment (null for future forecast)", json_schema_extra={"example": 236.0})
    total_predicted_demand: Optional[float] = Field(None, description="Total predicted demand (lag-1 baseline for historical, baseline forecast for future)", json_schema_extra={"example": 236.0})
    is_forecast: bool = Field(False, description="Flag indicating if this entry is a future forecast period", json_schema_extra={"example": False})


class MonthlyDemandResponse(BaseModel):
    """Monthly timeline of aggregated demand history and next-month forecast."""

    forecast_period: ForecastPeriod
    filter_equipment: Optional[str] = Field(None, description="Equipment filter applied, if any")
    filter_category: Optional[str] = Field(None, description="Equipment category filter applied, if any")
    total_periods: int = Field(..., description="Number of timeline data points returned", json_schema_extra={"example": 32})
    timeline: List[MonthlyDemandRecord]


class ModelComparisonItem(BaseModel):
    """Validation performance benchmark for an evaluated model."""

    model: str = Field(..., description="Model name", json_schema_extra={"example": "Previous-Month Baseline"})
    mae: float = Field(..., description="Mean Absolute Error", json_schema_extra={"example": 4.5893})
    rmse: float = Field(..., description="Root Mean Squared Error", json_schema_extra={"example": 5.8858})
    r2: Optional[float] = Field(None, description="R-squared metric (may be negative or nan for underperforming baselines)", json_schema_extra={"example": 0.4595})


class ModelComparisonResponse(BaseModel):
    """Comparison of models evaluated during the ML phase as documented in PRD."""

    selected_model: str = Field(..., description="The chosen model deployed for production forecasting", json_schema_extra={"example": "Previous-Month Baseline"})
    rationale: str = Field(..., description="Justification for selecting the model per PRD", json_schema_extra={"example": "The Previous-Month Baseline achieved lowest MAE and RMSE on the time-aware test set."})
    models: List[ModelComparisonItem]


class EquipmentInfo(BaseModel):
    """Basic equipment information including category."""

    equipment: str = Field(..., description="Name of the medical equipment", json_schema_extra={"example": "Oxygen Concentrator"})
    category: str = Field(..., description="Equipment category classification", json_schema_extra={"example": "Respiratory Equipment"})

