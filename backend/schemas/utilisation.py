"""Pydantic schemas for the Equipment Utilisation module."""

from typing import List
from pydantic import BaseModel, Field


class AnalysisPeriod(BaseModel):
    """Analysis timeframe over which planned equipment utilisation is calculated."""

    start_date: str = Field(..., description="Start date of the analysis window", json_schema_extra={"example": "2024-01-01"})
    end_date: str = Field(..., description="End date of the analysis window", json_schema_extra={"example": "2026-07-31"})
    total_days: int = Field(..., description="Total elapsed days within the analysis window", json_schema_extra={"example": 943})


class UtilisationThresholds(BaseModel):
    """Data-driven quartile thresholds for utilisation status classification."""

    low_threshold_percentage: float = Field(..., description="25th percentile threshold below which equipment is under-utilised", json_schema_extra={"example": 17.82})
    high_threshold_percentage: float = Field(..., description="75th percentile threshold above which equipment is highly utilised", json_schema_extra={"example": 24.18})


class EquipmentUtilisationItem(BaseModel):
    """Utilisation metrics, classification, and availability for a single medical equipment type."""

    equipment: str = Field(..., description="Name of the medical equipment", json_schema_extra={"example": "Oxygen Concentrator"})
    category: str = Field(..., description="Equipment category classification", json_schema_extra={"example": "Respiratory Equipment"})
    total_inventory: int = Field(..., description="Total inventory unit pool size", json_schema_extra={"example": 16})
    planned_rental_days: float = Field(..., description="Total planned rental days within the analysis period", json_schema_extra={"example": 4316.0})
    available_equipment_days: float = Field(..., description="Total available equipment days (inventory × analysis days)", json_schema_extra={"example": 15088.0})
    utilisation_percentage: float = Field(..., description="Planned utilisation percentage", json_schema_extra={"example": 28.61})
    utilisation_status: str = Field(..., description="Quartile classification: Highly Utilised, Moderately Utilised, or Under Utilised", json_schema_extra={"example": "Highly Utilised"})
    currently_rented: int = Field(..., description="Currently rented units as of the snapshot date", json_schema_extra={"example": 7})
    currently_available: int = Field(..., description="Currently available units as of the snapshot date", json_schema_extra={"example": 9})
    actionable_insight: str = Field(..., description="Operational interpretation of utilisation and availability", json_schema_extra={"example": "Oxygen Concentrator has high utilisation (28.61%) and 9 unit(s) currently available."})


class EquipmentUtilisationDetailResponse(BaseModel):
    """Detailed utilisation response for a specific equipment type."""

    equipment: str = Field(..., description="Name of the medical equipment", json_schema_extra={"example": "Oxygen Concentrator"})
    category: str = Field(..., description="Equipment category classification", json_schema_extra={"example": "Respiratory Equipment"})
    analysis_period: AnalysisPeriod
    as_of_date: str = Field(..., description="Current availability snapshot reference date", json_schema_extra={"example": "2026-07-31"})
    total_inventory: int = Field(..., description="Total inventory unit pool size", json_schema_extra={"example": 16})
    planned_rental_days: float = Field(..., description="Total planned rental days", json_schema_extra={"example": 4316.0})
    available_equipment_days: float = Field(..., description="Total available equipment days", json_schema_extra={"example": 15088.0})
    utilisation_percentage: float = Field(..., description="Planned utilisation percentage", json_schema_extra={"example": 28.61})
    utilisation_status: str = Field(..., description="Utilisation status", json_schema_extra={"example": "Highly Utilised"})
    currently_rented: int = Field(..., description="Currently rented units", json_schema_extra={"example": 7})
    currently_available: int = Field(..., description="Currently available units", json_schema_extra={"example": 9})
    actionable_insight: str = Field(..., description="Actionable insight", json_schema_extra={"example": "Oxygen Concentrator has high utilisation (28.61%) and 9 unit(s) currently available."})


class OverallUtilisationResponse(BaseModel):
    """Overall dashboard response covering aggregate utilisation, thresholds, and equipment summaries."""

    analysis_period: AnalysisPeriod
    as_of_date: str = Field(..., description="Current availability snapshot reference date", json_schema_extra={"example": "2026-07-31"})
    average_utilisation: float = Field(..., description="Mean utilisation percentage across all equipment types", json_schema_extra={"example": 21.08})
    minimum_utilisation: float = Field(..., description="Minimum equipment utilisation percentage", json_schema_extra={"example": 12.43})
    maximum_utilisation: float = Field(..., description="Maximum equipment utilisation percentage", json_schema_extra={"example": 31.78})
    total_inventory: int = Field(..., description="Total inventory count across all equipment pools", json_schema_extra={"example": 202})
    total_currently_rented: int = Field(..., description="Total currently active rentals across all equipment", json_schema_extra={"example": 102})
    total_currently_available: int = Field(..., description="Total currently available units across all equipment", json_schema_extra={"example": 100})
    thresholds: UtilisationThresholds
    equipment_count: int = Field(..., description="Total distinct equipment types tracked", json_schema_extra={"example": 16})
    equipments: List[EquipmentUtilisationItem]


class CategoryUtilisationItem(BaseModel):
    """Utilisation metrics for a medical equipment category."""

    category: str = Field(..., description="Equipment category name", json_schema_extra={"example": "Mobility Equipment"})
    planned_rental_days: float = Field(..., description="Aggregated planned rental days for category", json_schema_extra={"example": 9309.0})
    available_equipment_days: float = Field(..., description="Aggregated available equipment days for category", json_schema_extra={"example": 34891.0})
    total_inventory: int = Field(..., description="Total inventory units in category", json_schema_extra={"example": 37})
    utilisation_percentage: float = Field(..., description="Aggregated category utilisation percentage", json_schema_extra={"example": 26.68})
    rank: int = Field(..., description="Utilisation rank (1 = highest utilisation)", json_schema_extra={"example": 1})


class CategoryUtilisationResponse(BaseModel):
    """Category-wise utilisation ranking response."""

    total_categories: int = Field(..., description="Number of equipment categories", json_schema_extra={"example": 7})
    categories: List[CategoryUtilisationItem]


class EquipmentAvailabilityItem(BaseModel):
    """Availability status for an individual equipment type."""

    equipment: str = Field(..., description="Name of the medical equipment", json_schema_extra={"example": "Oxygen Concentrator"})
    category: str = Field(..., description="Equipment category classification", json_schema_extra={"example": "Respiratory Equipment"})
    total_inventory: int = Field(..., description="Total inventory unit count", json_schema_extra={"example": 16})
    currently_rented: int = Field(..., description="Currently active rented units", json_schema_extra={"example": 7})
    currently_available: int = Field(..., description="Currently available units for immediate rental", json_schema_extra={"example": 9})
    availability_rate_percentage: float = Field(..., description="Percentage of inventory currently available", json_schema_extra={"example": 56.25})


class AvailabilitySnapshotResponse(BaseModel):
    """Current warehouse inventory availability snapshot."""

    as_of_date: str = Field(..., description="Snapshot reference date", json_schema_extra={"example": "2026-07-31"})
    total_inventory: int = Field(..., description="Total inventory count across all equipment", json_schema_extra={"example": 202})
    total_rented: int = Field(..., description="Total rented units across all equipment", json_schema_extra={"example": 102})
    total_available: int = Field(..., description="Total available units across all equipment", json_schema_extra={"example": 100})
    equipment_count: int = Field(..., description="Number of equipment types", json_schema_extra={"example": 16})
    equipments: List[EquipmentAvailabilityItem]
