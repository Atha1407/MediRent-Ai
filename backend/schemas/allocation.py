"""Pydantic schemas for the Smart Equipment Allocation module."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class AllocationRequest(BaseModel):
    """Customer rental request payload for smart equipment allocation."""

    equipment: str = Field(
        ...,
        description="Name of the medical equipment type requested",
        json_schema_extra={"example": "Oxygen Concentrator"},
    )
    rental_duration_days: int = Field(
        ...,
        gt=0,
        description="Requested rental duration in days (must be positive integer)",
        json_schema_extra={"example": 12},
    )
    request_start: str = Field(
        ...,
        description="Requested rental start date in YYYY-MM-DD format",
        json_schema_extra={"example": "2026-07-31"},
    )
    strict_maintenance: bool = Field(
        default=False,
        description="Whether to enforce strict maintenance filtering (exclude units with past overdue maintenance)",
        json_schema_extra={"example": False},
    )
    exclude_rental_id: Optional[str] = Field(
        default=None,
        description="Rental ID to exclude from decision snapshot (used for historical simulation/evaluation)",
        json_schema_extra={"example": None},
    )

    @model_validator(mode="before")
    @classmethod
    def handle_request_start_alias(cls, data):
        """Accept request_start_date as an alias for request_start if provided."""
        if isinstance(data, dict):
            if "request_start" not in data and "request_start_date" in data:
                data["request_start"] = data["request_start_date"]
        return data


class CandidateUnitItem(BaseModel):
    """Detailed scores and operational metrics for an evaluated candidate equipment unit."""

    rank: int = Field(..., description="Suitability rank (1 = recommended best unit)", json_schema_extra={"example": 1})
    equipment_id: str = Field(..., description="Unique physical equipment unit ID", json_schema_extra={"example": "OC-014"})
    equipment: str = Field(..., description="Equipment type name", json_schema_extra={"example": "Oxygen Concentrator"})
    condition: str = Field(..., description="Normalized equipment condition (Excellent, Good, Fair, Poor, Unknown)", json_schema_extra={"example": "Good"})
    suitability_score: float = Field(..., description="Composite suitability score (0-100)", json_schema_extra={"example": 92.38})
    availability_score: float = Field(default=100.0, description="Availability component score (15% weight)", json_schema_extra={"example": 100.0})
    condition_score: float = Field(..., description="Condition component score (20% weight)", json_schema_extra={"example": 85.0})
    maintenance_score: float = Field(..., description="Maintenance component score (20% weight)", json_schema_extra={"example": 100.0})
    availability_window_score: float = Field(..., description="Availability window component score (15% weight)", json_schema_extra={"example": 100.0})
    duration_fit_score: float = Field(..., description="Duration fit component score (10% weight)", json_schema_extra={"example": 100.0})
    current_utilisation_score: float = Field(..., description="Current unit utilisation component score (15% weight)", json_schema_extra={"example": 84.87})
    future_demand_score: float = Field(..., description="Future demand component score (5% weight)", json_schema_extra={"example": 7.58})
    current_unit_utilisation_percentage: float = Field(..., description="Historical unit-level utilisation percentage up to request date", json_schema_extra={"example": 24.63})
    current_unit_utilisation_pct: Optional[float] = Field(None, description="Convenience alias for current_unit_utilisation_percentage", json_schema_extra={"example": 24.63})
    availability_window_days: float = Field(..., description="Free days before next scheduled reservation", json_schema_extra={"example": 3650.0})
    next_booked_start: Optional[str] = Field(None, description="Date of next scheduled booking if any", json_schema_extra={"example": None})
    next_maintenance_due: Optional[str] = Field(None, description="Date of next scheduled maintenance if any", json_schema_extra={"example": "2026-11-15"})


class NextAvailableOptionItem(BaseModel):
    """Soonest available unit option when no unit satisfies immediate request constraints."""

    equipment_id: str = Field(..., description="Equipment unit ID", json_schema_extra={"example": "WK-001"})
    equipment: str = Field(..., description="Equipment type name", json_schema_extra={"example": "Walker"})
    condition: Optional[str] = Field(None, description="Equipment physical condition", json_schema_extra={"example": "Good"})
    current_return_date: Optional[str] = Field(None, description="Expected return date of active rental", json_schema_extra={"example": "2026-08-05"})
    expected_available_date: Optional[str] = Field(None, description="Projected date unit will become available", json_schema_extra={"example": "2026-08-05"})


class AllocationRecommendationResponse(BaseModel):
    """Complete smart allocation recommendation decision response."""

    recommendation_status: str = Field(
        ...,
        description="Recommendation status: 'Recommended' or 'No suitable unit currently available'",
        json_schema_extra={"example": "Recommended"},
    )
    equipment: str = Field(..., description="Requested equipment type", json_schema_extra={"example": "Oxygen Concentrator"})
    request_start_date: str = Field(..., description="Rental request start date", json_schema_extra={"example": "2026-07-31"})
    request_end_date: str = Field(..., description="Computed rental request end date", json_schema_extra={"example": "2026-08-12"})
    rental_duration_days: int = Field(..., description="Requested duration in days", json_schema_extra={"example": 12})
    recommended_equipment_id: Optional[str] = Field(
        None,
        description="Recommended physical equipment unit ID",
        json_schema_extra={"example": "OC-014"},
    )
    suitability_score: Optional[float] = Field(
        None,
        description="Composite suitability score (0-100) of recommended unit",
        json_schema_extra={"example": 92.38},
    )
    condition: Optional[str] = Field(
        None,
        description="Condition of recommended unit",
        json_schema_extra={"example": "Good"},
    )
    maintenance_status: Optional[str] = Field(
        None,
        description="Maintenance classification: 'Not Due', 'Due Soon', 'Due During Rental', 'Overdue', or 'Unknown'",
        json_schema_extra={"example": "Not Due"},
    )
    availability_window_days: Optional[float] = Field(
        None,
        description="Days available before next scheduled commitment",
        json_schema_extra={"example": 3650.0},
    )
    current_unit_utilisation_percentage: Optional[float] = Field(
        None,
        description="Historical unit-level utilisation percentage up to request date",
        json_schema_extra={"example": 24.63},
    )
    current_unit_utilisation_pct: Optional[float] = Field(
        None,
        description="Convenience alias for current_unit_utilisation_percentage",
        json_schema_extra={"example": 24.63},
    )
    predicted_future_demand: Optional[float] = Field(
        None,
        description="Predicted future demand context for this equipment type",
        json_schema_extra={"example": 24.33},
    )
    reason: str = Field(
        ...,
        description="Natural language explanation of the allocation decision",
        json_schema_extra={"example": "Good condition; maintenance status: Not Due; no known upcoming booking; current unit utilisation is 24.6%; future demand is high, so a less-utilised unit is preferred."},
    )
    candidates: List[CandidateUnitItem] = Field(
        default_factory=list,
        description="Ranked list of all evaluated candidate units satisfying hard constraints",
    )
    next_available_options: List[NextAvailableOptionItem] = Field(
        default_factory=list,
        description="Alternative unit options when no unit satisfies current constraints",
    )

    # Notebook-compatible title-cased aliases
    Recommendation_Status: Optional[str] = Field(None, description="Title-cased notebook compatibility alias")
    Recommended_Equipment_ID: Optional[str] = Field(None, description="Title-cased notebook compatibility alias")
    Suitability_Score: Optional[float] = Field(None, description="Title-cased notebook compatibility alias")
    Condition: Optional[str] = Field(None, description="Title-cased notebook compatibility alias")
    Maintenance_Status: Optional[str] = Field(None, description="Title-cased notebook compatibility alias")
    Availability_Window_Days: Optional[float] = Field(None, description="Title-cased notebook compatibility alias")
    Reason: Optional[str] = Field(None, description="Title-cased notebook compatibility alias")


class AllocationMetadataResponse(BaseModel):
    """Operational metadata and scoring policy configuration for Smart Equipment Allocation."""

    status: str = Field(default="operational", description="Allocation engine operational status", json_schema_extra={"example": "operational"})
    total_units: int = Field(..., description="Total physical units catalogued across all pools", json_schema_extra={"example": 202})
    total_equipment_types: int = Field(..., description="Total distinct equipment types tracked", json_schema_extra={"example": 16})
    weights: Dict[str, float] = Field(..., description="Decision policy scoring component weights")
    default_strict_maintenance: bool = Field(default=False, description="Default strict maintenance filtering policy")
    equipment_list: List[str] = Field(..., description="List of all tracked medical equipment types")
