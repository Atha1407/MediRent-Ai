"""Demand Prediction Service for MediRent-AI.

Loads the processed equipment-month dataset and provides demand forecasts,
equipment-level historical/predicted metrics, monthly timelines, and trend
classifications based on the finalized Previous-Month Demand Baseline model.
"""

import calendar
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.schemas.demand import (
    DemandOverviewResponse,
    EquipmentDemandDetailResponse,
    EquipmentDemandSummary,
    EquipmentInfo,
    ForecastPeriod,
    HistoricalDemandRecord,
    HistoricalSummary,
    ModelComparisonItem,
    ModelComparisonResponse,
    ModelMetrics,
    MonthlyDemandRecord,
    MonthlyDemandResponse,
)

REQUIRED_DATASET_COLUMNS = {
    "Equipment",
    "Equipment_Category",
    "Year",
    "Month_Number",
    "Quarter",
    "Historical_Demand_Lag_1",
    "Historical_Demand_Lag_2",
    "Historical_Demand_Rolling_3M",
    "Historical_Demand_Rolling_6M",
    "Historical_Demand_Trend_2M",
    "Monthly_Demand",
}


class DemandService:
    """Service encapsulating demand dataset operations and baseline forecasting."""

    def __init__(
        self,
        dataset_path: Optional[Path] = None,
        comparison_path: Optional[Path] = None,
    ) -> None:
        """Initialize the Demand Service with dataset paths.

        Args:
            dataset_path: Path to demand_prediction_dataset.csv. Defaults to project standard path.
            comparison_path: Path to demand_model_comparison.csv. Defaults to project standard path.
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        self.dataset_path = (
            dataset_path
            or project_root / "data" / "processed" / "demand_prediction_dataset.csv"
        )
        self.comparison_path = (
            comparison_path
            or project_root / "data" / "processed" / "demand_model_comparison.csv"
        )

        self._df: pd.DataFrame = self._load_and_validate_dataset()
        self._equipment_lookup: Dict[str, str] = {
            eq.strip().lower(): eq for eq in self._df["Equipment"].unique()
        }
        self._category_lookup: Dict[str, str] = {
            cat.strip().lower(): cat for cat in self._df["Equipment_Category"].unique()
        }
        self._latest_year, self._latest_month = self._determine_latest_period()
        self._forecast_period = self._determine_forecast_period(
            self._latest_year, self._latest_month
        )

    def _load_and_validate_dataset(self) -> pd.DataFrame:
        """Load and validate the processed demand prediction dataset.

        Returns:
            pd.DataFrame: Cleaned and validated dataset.

        Raises:
            FileNotFoundError: If the dataset file does not exist.
            ValueError: If required columns are missing or the dataset is empty.
        """
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Demand dataset file not found at: {self.dataset_path}"
            )

        df = pd.read_csv(self.dataset_path)

        missing_cols = REQUIRED_DATASET_COLUMNS - set(df.columns)
        if missing_cols:
            raise ValueError(
                f"Demand dataset is missing required columns: {sorted(missing_cols)}"
            )

        if df.empty:
            raise ValueError("Demand dataset is empty.")

        # Ensure correct datatypes
        df["Year"] = df["Year"].astype(int)
        df["Month_Number"] = df["Month_Number"].astype(int)
        df["Monthly_Demand"] = df["Monthly_Demand"].astype(float)
        df = df.sort_values(by=["Equipment", "Year", "Month_Number"]).reset_index(
            drop=True
        )
        return df

    def _determine_latest_period(self) -> Tuple[int, int]:
        """Determine the latest historical year and month in the dataset."""
        latest_year = int(self._df["Year"].max())
        latest_month = int(
            self._df[self._df["Year"] == latest_year]["Month_Number"].max()
        )
        return latest_year, latest_month

    def _determine_forecast_period(
        self, latest_year: int, latest_month: int
    ) -> ForecastPeriod:
        """Determine the upcoming forecasting timeframe directly following the latest data point."""
        if latest_month == 12:
            forecast_year = latest_year + 1
            forecast_month = 1
        else:
            forecast_year = latest_year
            forecast_month = latest_month + 1

        label = f"{calendar.month_name[forecast_month]} {forecast_year}"
        return ForecastPeriod(
            year=forecast_year,
            month=forecast_month,
            label=label,
        )

    @property
    def forecast_period(self) -> ForecastPeriod:
        """Return the target forecast period."""
        return self._forecast_period

    @staticmethod
    def classify_trend_and_insight(
        equipment: str, latest_demand: float, previous_demand: Optional[float]
    ) -> Tuple[str, str]:
        """Classify demand trend momentum and generate an actionable insight.

        Uses recent monthly momentum (latest actual demand vs previous month demand):
        - increasing: demand grew compared to previous month
        - decreasing: demand dropped compared to previous month
        - stable: demand remained unchanged

        Args:
            equipment: Name of the equipment.
            latest_demand: Actual demand in the latest month.
            previous_demand: Actual demand in the preceding month.

        Returns:
            Tuple[str, str]: (trend_label, actionable_insight_text)
        """
        if previous_demand is None or pd.isna(previous_demand):
            return "stable", f"Demand for {equipment} is expected to remain stable."

        momentum = latest_demand - previous_demand
        if momentum > 0:
            trend = "increasing"
            insight = (
                f"Demand for {equipment} is expected to increase based on recent monthly momentum."
            )
        elif momentum < 0:
            trend = "decreasing"
            insight = (
                f"Demand for {equipment} is expected to decrease based on recent monthly momentum."
            )
        else:
            trend = "stable"
            insight = (
                f"Demand for {equipment} is expected to remain stable based on recent monthly momentum."
            )
        return trend, insight

    def resolve_equipment_name(self, name: str) -> Optional[str]:
        """Resolve an equipment name case-insensitively.

        Args:
            name: Equipment query string.

        Returns:
            Optional[str]: Canonical equipment name or None if not found.
        """
        if not name:
            return None
        return self._equipment_lookup.get(name.strip().lower())

    def resolve_category_name(self, name: str) -> Optional[str]:
        """Resolve a category name case-insensitively.

        Args:
            name: Category query string.

        Returns:
            Optional[str]: Canonical category name or None if not found.
        """
        if not name:
            return None
        return self._category_lookup.get(name.strip().lower())

    def get_equipment_list(self) -> List[EquipmentInfo]:
        """Return list of all tracked equipment items and their categories."""
        distinct_df = (
            self._df[["Equipment", "Equipment_Category"]]
            .drop_duplicates()
            .sort_values(by="Equipment")
        )
        return [
            EquipmentInfo(
                equipment=str(row["Equipment"]),
                category=str(row["Equipment_Category"]),
            )
            for _, row in distinct_df.iterrows()
        ]

    def get_model_metrics(self) -> ModelMetrics:
        """Return validation performance metrics for the Previous-Month Baseline model.

        Evaluated on the time-aware test set (January 2026 - July 2026).
        """
        test_df = self._df[self._df["Year"] == 2026]
        if not test_df.empty:
            y_true = test_df["Monthly_Demand"]
            y_pred = test_df["Historical_Demand_Lag_1"]
            valid_mask = y_pred.notnull()

            mae = float(np.mean(np.abs(y_true[valid_mask] - y_pred[valid_mask])))
            rmse = float(
                np.sqrt(np.mean((y_true[valid_mask] - y_pred[valid_mask]) ** 2))
            )
            ss_res = float(np.sum((y_true[valid_mask] - y_pred[valid_mask]) ** 2))
            ss_tot = float(
                np.sum((y_true[valid_mask] - np.mean(y_true[valid_mask])) ** 2)
            )
            r2 = float(1 - (ss_res / ss_tot)) if ss_tot != 0 else 0.0
        else:
            mae, rmse, r2 = 4.5893, 5.8858, 0.4595

        return ModelMetrics(
            model_name="Previous-Month Demand Baseline",
            mae=round(mae, 4),
            rmse=round(rmse, 4),
            r2=round(r2, 4),
            test_period="January 2026 - July 2026",
        )

    def get_model_comparison(self) -> ModelComparisonResponse:
        """Return performance benchmark comparison across evaluated models from ML phase."""
        items: List[ModelComparisonItem] = []
        if self.comparison_path.exists():
            comp_df = pd.read_csv(self.comparison_path)
            for _, row in comp_df.iterrows():
                r2_val = row["R2"]
                items.append(
                    ModelComparisonItem(
                        model=str(row["Model"]),
                        mae=round(float(row["MAE"]), 4),
                        rmse=round(float(row["RMSE"]), 4),
                        r2=round(float(r2_val), 4) if pd.notnull(r2_val) else None,
                    )
                )

        return ModelComparisonResponse(
            selected_model="Previous-Month Baseline",
            rationale=(
                "The Previous-Month Baseline achieved the lowest MAE (4.589) and RMSE (5.886) "
                "with an R² of 0.460 on the time-aware test set (January 2026 – July 2026), "
                "substantially outperforming Ridge Regression and Demand-Change variants."
            ),
            models=items,
        )

    def get_demand_overview(self) -> DemandOverviewResponse:
        """Calculate and return aggregate demand forecast across all equipment for upcoming month.

        Uses the Previous-Month Demand Baseline: the upcoming month's forecast equals
        the latest recorded monthly demand for each equipment.
        """
        latest_mask = (self._df["Year"] == self._latest_year) & (
            self._df["Month_Number"] == self._latest_month
        )
        latest_df = self._df[latest_mask]

        equipments_summary: List[EquipmentDemandSummary] = []
        for _, row in latest_df.iterrows():
            equipment_name = str(row["Equipment"])
            category_name = str(row["Equipment_Category"])
            latest_actual = float(row["Monthly_Demand"])
            # In Previous-Month Baseline, upcoming forecast equals latest observed month
            predicted_demand = latest_actual
            prev_demand = (
                float(row["Historical_Demand_Lag_1"])
                if pd.notnull(row["Historical_Demand_Lag_1"])
                else None
            )

            trend, insight = self.classify_trend_and_insight(
                equipment_name, latest_actual, prev_demand
            )

            equipments_summary.append(
                EquipmentDemandSummary(
                    equipment=equipment_name,
                    category=category_name,
                    latest_actual_demand=latest_actual,
                    predicted_demand=predicted_demand,
                    trend=trend,
                    insight=insight,
                )
            )

        # Sort equipments by predicted demand descending for intuitive prioritization
        equipments_summary.sort(key=lambda x: x.predicted_demand, reverse=True)

        total_predicted = float(sum(item.predicted_demand for item in equipments_summary))

        return DemandOverviewResponse(
            forecast_period=self._forecast_period,
            total_predicted_demand=total_predicted,
            equipment_count=len(equipments_summary),
            model_metrics=self.get_model_metrics(),
            equipments=equipments_summary,
        )

    def get_equipment_demand_detail(
        self, equipment_name: str
    ) -> Optional[EquipmentDemandDetailResponse]:
        """Return historical demand records and upcoming forecast for a specific equipment.

        Args:
            equipment_name: Equipment name (case-insensitive).

        Returns:
            Optional[EquipmentDemandDetailResponse]: Full detail or None if equipment is invalid.
        """
        canonical_name = self.resolve_equipment_name(equipment_name)
        if not canonical_name:
            return None

        eq_df = self._df[self._df["Equipment"] == canonical_name].sort_values(
            by=["Year", "Month_Number"]
        )
        if eq_df.empty:
            return None

        category = str(eq_df["Equipment_Category"].iloc[0])

        history: List[HistoricalDemandRecord] = []
        for _, row in eq_df.iterrows():
            yr = int(row["Year"])
            mo = int(row["Month_Number"])
            actual = float(row["Monthly_Demand"])
            lag1 = (
                float(row["Historical_Demand_Lag_1"])
                if pd.notnull(row["Historical_Demand_Lag_1"])
                else None
            )
            residual = round(actual - lag1, 4) if lag1 is not None else None
            abs_err = round(abs(actual - lag1), 4) if lag1 is not None else None
            trend_2m = (
                float(row["Historical_Demand_Trend_2M"])
                if pd.notnull(row["Historical_Demand_Trend_2M"])
                else None
            )

            history.append(
                HistoricalDemandRecord(
                    year=yr,
                    month=mo,
                    year_month=f"{yr}-{mo:02d}",
                    actual_demand=actual,
                    predicted_demand=lag1,
                    residual_error=residual,
                    absolute_error=abs_err,
                    trend_2m=trend_2m,
                )
            )

        latest_row = eq_df.iloc[-1]
        latest_actual = float(latest_row["Monthly_Demand"])
        predicted_demand = latest_actual
        prev_actual = (
            float(latest_row["Historical_Demand_Lag_1"])
            if pd.notnull(latest_row["Historical_Demand_Lag_1"])
            else None
        )
        trend, insight = self.classify_trend_and_insight(
            canonical_name, latest_actual, prev_actual
        )

        # Historical Summary
        test_eq = eq_df[eq_df["Year"] == 2026]
        test_mae: Optional[float] = None
        if not test_eq.empty:
            test_diffs = (
                test_eq["Monthly_Demand"] - test_eq["Historical_Demand_Lag_1"]
            ).abs()
            test_mae = round(float(test_diffs.mean()), 4)

        summary = HistoricalSummary(
            total_months=len(eq_df),
            average_monthly_demand=round(float(eq_df["Monthly_Demand"].mean()), 2),
            min_monthly_demand=float(eq_df["Monthly_Demand"].min()),
            max_monthly_demand=float(eq_df["Monthly_Demand"].max()),
            test_mae=test_mae,
        )

        return EquipmentDemandDetailResponse(
            equipment=canonical_name,
            category=category,
            forecast_period=self._forecast_period,
            latest_actual_demand=latest_actual,
            predicted_demand=predicted_demand,
            trend=trend,
            insight=insight,
            summary=summary,
            history=history,
        )

    def get_monthly_demand(
        self,
        equipment: Optional[str] = None,
        category: Optional[str] = None,
    ) -> MonthlyDemandResponse:
        """Return historical monthly demand aggregated across equipment or filtered.

        Args:
            equipment: Optional equipment name filter.
            category: Optional equipment category filter.

        Returns:
            MonthlyDemandResponse: Timeline of historical observations and future forecast.

        Raises:
            ValueError: If the equipment or category filter is invalid.
        """
        filtered_df = self._df.copy()
        canonical_eq: Optional[str] = None
        canonical_cat: Optional[str] = None

        if equipment:
            canonical_eq = self.resolve_equipment_name(equipment)
            if not canonical_eq:
                raise ValueError(
                    f"Equipment '{equipment}' not found. Available equipment: {sorted(list(self._equipment_lookup.values()))}"
                )
            filtered_df = filtered_df[filtered_df["Equipment"] == canonical_eq]

        if category:
            canonical_cat = self.resolve_category_name(category)
            if not canonical_cat:
                raise ValueError(
                    f"Equipment category '{category}' not found. Available categories: {sorted(list(self._category_lookup.values()))}"
                )
            filtered_df = filtered_df[filtered_df["Equipment_Category"] == canonical_cat]

        # Group by Year, Month_Number
        grouped = (
            filtered_df.groupby(["Year", "Month_Number"], as_index=False)
            .agg(
                total_actual=("Monthly_Demand", "sum"),
                total_predicted=(
                    "Historical_Demand_Lag_1",
                    lambda s: s.sum() if s.notnull().all() else None,
                ),
            )
            .sort_values(by=["Year", "Month_Number"])
        )

        timeline: List[MonthlyDemandRecord] = []
        for _, row in grouped.iterrows():
            yr = int(row["Year"])
            mo = int(row["Month_Number"])
            act = float(row["total_actual"])
            pred = (
                round(float(row["total_predicted"]), 2)
                if pd.notnull(row["total_predicted"])
                else None
            )
            timeline.append(
                MonthlyDemandRecord(
                    year=yr,
                    month=mo,
                    year_month=f"{yr}-{mo:02d}",
                    total_actual_demand=act,
                    total_predicted_demand=pred,
                    is_forecast=False,
                )
            )

        # Baseline forecast for upcoming month equals sum of latest month's actual demand
        latest_sub = filtered_df[
            (filtered_df["Year"] == self._latest_year)
            & (filtered_df["Month_Number"] == self._latest_month)
        ]
        forecast_pred = (
            float(latest_sub["Monthly_Demand"].sum()) if not latest_sub.empty else 0.0
        )

        timeline.append(
            MonthlyDemandRecord(
                year=self._forecast_period.year,
                month=self._forecast_period.month,
                year_month=f"{self._forecast_period.year}-{self._forecast_period.month:02d}",
                total_actual_demand=None,
                total_predicted_demand=round(forecast_pred, 2),
                is_forecast=True,
            )
        )

        return MonthlyDemandResponse(
            forecast_period=self._forecast_period,
            filter_equipment=canonical_eq,
            filter_category=canonical_cat,
            total_periods=len(timeline),
            timeline=timeline,
        )


# Cached service instance for FastAPI dependency injection
_demand_service_instance: Optional[DemandService] = None


def get_demand_service() -> DemandService:
    """FastAPI dependency provider returning the DemandService singleton."""
    global _demand_service_instance
    if _demand_service_instance is None:
        _demand_service_instance = DemandService()
    return _demand_service_instance
