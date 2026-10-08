"""Revenue Prediction Service for MediRent-AI.

Loads the finalized revenue prediction datasets and provides Demand-Based Revenue forecasts,
monthly historical vs predicted revenue timelines, validation benchmarks, and dashboard-ready summaries.
"""

import calendar
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from backend.schemas.revenue import (
    ForecastPeriod,
    HistoricalPeriod,
    HistoricalRevenueRecord,
    MonthlyRevenueRecord,
    MonthlyRevenueResponse,
    RevenueModelComparisonItem,
    RevenueModelComparisonResponse,
    RevenueModelMetrics,
    RevenueOverviewResponse,
    RevenueSummaryStatistics,
)

REQUIRED_PREDICTIONS_COLUMNS = {
    "Month",
    "Monthly_Revenue",
    "Predicted_Revenue",
    "Error",
    "Absolute_Error",
}

REQUIRED_COMPARISON_COLUMNS = {"Model", "MAE", "RMSE", "R2"}

# Finalized training-period average revenue per rental as evaluated in ML phase
DEFAULT_AVG_REVENUE_PER_RENTAL = 4186.802651215859


class RevenueService:
    """Service encapsulating revenue prediction data operations and demand-based forecasting."""

    def __init__(
        self,
        predictions_path: Optional[Path] = None,
        comparison_path: Optional[Path] = None,
        features_path: Optional[Path] = None,
        demand_path: Optional[Path] = None,
    ) -> None:
        """Initialize the Revenue Service with dataset paths.

        Args:
            predictions_path: Path to revenue_predictions.csv.
            comparison_path: Path to revenue_model_comparison.csv.
            features_path: Optional path to feature_engineered_medical_equipment_dataset.csv for full history.
            demand_path: Optional path to demand_prediction_dataset.csv for expected rental volume.
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        self.predictions_path = (
            predictions_path
            or project_root / "data" / "processed" / "revenue_predictions.csv"
        )
        self.comparison_path = (
            comparison_path
            or project_root / "data" / "processed" / "revenue_model_comparison.csv"
        )
        self.features_path = (
            features_path
            or project_root
            / "data"
            / "processed"
            / "feature_engineered_medical_equipment_dataset.csv"
        )
        self.demand_path = (
            demand_path
            or project_root / "data" / "processed" / "demand_prediction_dataset.csv"
        )

        self._predictions_df = self._load_and_validate_predictions()
        self._comparison_df = self._load_and_validate_comparison()
        self._full_historical_revenue: Dict[str, float] = self._load_full_history()

        self._latest_year, self._latest_month, self._latest_revenue = (
            self._determine_latest_period()
        )
        self._forecast_period = self._determine_forecast_period(
            self._latest_year, self._latest_month
        )
        self._historical_period = HistoricalPeriod(
            year=self._latest_year,
            month=self._latest_month,
            label=f"{calendar.month_name[self._latest_month]} {self._latest_year}",
        )
        self._expected_rental_volume = self._determine_expected_rental_volume()
        self._avg_revenue_per_rental = self._determine_avg_revenue_per_rental()

    def _load_and_validate_predictions(self) -> pd.DataFrame:
        """Load and validate the finalized revenue predictions dataset."""
        if not self.predictions_path.exists():
            raise FileNotFoundError(
                f"Revenue predictions file not found at: {self.predictions_path}"
            )

        df = pd.read_csv(self.predictions_path)

        missing = REQUIRED_PREDICTIONS_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"Revenue predictions file is missing required columns: {sorted(missing)}"
            )

        if df.empty:
            raise ValueError("Revenue predictions file is empty.")

        # Ensure correct datatypes
        df["Monthly_Revenue"] = df["Monthly_Revenue"].astype(float)
        df["Predicted_Revenue"] = df["Predicted_Revenue"].astype(float)
        df["Error"] = df["Error"].astype(float)
        df["Absolute_Error"] = df["Absolute_Error"].astype(float)

        return df.sort_values(by="Month").reset_index(drop=True)

    def _load_and_validate_comparison(self) -> pd.DataFrame:
        """Load and validate the revenue model comparison dataset."""
        if not self.comparison_path.exists():
            raise FileNotFoundError(
                f"Revenue comparison file not found at: {self.comparison_path}"
            )

        df = pd.read_csv(self.comparison_path)

        missing = REQUIRED_COMPARISON_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"Revenue comparison file is missing required columns: {sorted(missing)}"
            )

        return df

    def _load_full_history(self) -> Dict[str, float]:
        """Load full 31-month historical revenue from feature engineered dataset if available.

        Falls back to predictions dataset if full dataset is not present.
        """
        history_map: Dict[str, float] = {}

        if self.features_path.exists():
            try:
                feat_df = pd.read_csv(
                    self.features_path,
                    usecols=["Rental_Start_Date", "Total_Rental_Amount"],
                )
                feat_df["Month"] = (
                    pd.to_datetime(feat_df["Rental_Start_Date"])
                    .dt.to_period("M")
                    .astype(str)
                )
                grouped = (
                    feat_df.groupby("Month")["Total_Rental_Amount"]
                    .sum()
                    .astype(float)
                )
                history_map = grouped.to_dict()
            except Exception:
                history_map = {}

        # Ensure all months in predictions_df are covered
        for _, row in self._predictions_df.iterrows():
            m = str(row["Month"])
            history_map[m] = float(row["Monthly_Revenue"])

        return history_map

    def _determine_latest_period(self) -> Tuple[int, int, float]:
        """Determine the latest historical year, month, and revenue in the dataset."""
        latest_row = self._predictions_df.iloc[-1]
        month_str = str(latest_row["Month"])
        parts = month_str.split("-")
        yr = int(parts[0])
        mo = int(parts[1])
        rev = float(latest_row["Monthly_Revenue"])
        return yr, mo, rev

    def _determine_forecast_period(
        self, latest_year: int, latest_month: int
    ) -> ForecastPeriod:
        """Determine the next forecasting timeframe following the latest data point."""
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

    def _determine_expected_rental_volume(self) -> float:
        """Determine the expected rental volume for next month based on Demand Baseline."""
        if self.demand_path.exists():
            try:
                demand_df = pd.read_csv(self.demand_path)
                latest_demand = demand_df[
                    (demand_df["Year"] == self._latest_year)
                    & (demand_df["Month_Number"] == self._latest_month)
                ]["Monthly_Demand"].sum()
                if latest_demand > 0:
                    return float(latest_demand)
            except Exception:
                pass
        return 236.0

    def _determine_avg_revenue_per_rental(self) -> float:
        """Return the finalized training-period average revenue per rental."""
        return DEFAULT_AVG_REVENUE_PER_RENTAL

    def get_model_metrics(self) -> RevenueModelMetrics:
        """Return validation performance metrics for the Demand-Based Revenue Forecasting model."""
        comp_match = self._comparison_df[
            self._comparison_df["Model"].str.contains(
                "Demand-Based", case=False, na=False
            )
        ]

        if not comp_match.empty:
            row = comp_match.iloc[0]
            mae = float(row["MAE"])
            rmse = float(row["RMSE"])
            r2 = float(row["R2"])
        else:
            mae, rmse, r2 = 142622.32, 172030.31, 0.3740

        return RevenueModelMetrics(
            model_name="Demand-Based Revenue Forecasting",
            mae=round(mae, 2),
            rmse=round(rmse, 2),
            r2=round(r2, 4),
            test_period="December 2025 - July 2026",
            methodology=(
                "Expected Revenue = Expected Rental Volume × Historical Average Revenue per Rental"
            ),
            avg_revenue_per_rental=round(self._avg_revenue_per_rental, 2),
        )

    def get_summary_statistics(self) -> RevenueSummaryStatistics:
        """Calculate summary statistics over the available historical monthly revenue series."""
        revenues = list(self._full_historical_revenue.values())
        if not revenues:
            revenues = self._predictions_df["Monthly_Revenue"].tolist()

        return RevenueSummaryStatistics(
            total_historical_months=len(revenues),
            average_monthly_revenue=round(float(sum(revenues) / len(revenues)), 2),
            min_monthly_revenue=round(float(min(revenues)), 2),
            max_monthly_revenue=round(float(max(revenues)), 2),
            total_historical_revenue=round(float(sum(revenues)), 2),
        )

    def get_revenue_overview(self) -> RevenueOverviewResponse:
        """Return aggregate revenue forecast overview for upcoming month and validation metrics."""
        predicted_revenue = round(
            self._expected_rental_volume * self._avg_revenue_per_rental, 2
        )

        test_records: List[HistoricalRevenueRecord] = []
        for _, row in self._predictions_df.iterrows():
            m_str = str(row["Month"])
            parts = m_str.split("-")
            test_records.append(
                HistoricalRevenueRecord(
                    year=int(parts[0]),
                    month=int(parts[1]),
                    year_month=m_str,
                    monthly_revenue=round(float(row["Monthly_Revenue"]), 2),
                    predicted_revenue=round(float(row["Predicted_Revenue"]), 2),
                    error=round(float(row["Error"]), 2),
                    absolute_error=round(float(row["Absolute_Error"]), 2),
                )
            )

        insight = (
            f"Expected revenue for {self._forecast_period.label} is ₹{predicted_revenue:,.2f} "
            f"based on {int(self._expected_rental_volume)} expected rentals at "
            f"₹{self._avg_revenue_per_rental:,.2f} average revenue per rental."
        )

        return RevenueOverviewResponse(
            forecast_period=self._forecast_period,
            latest_historical_period=self._historical_period,
            latest_historical_revenue=round(self._latest_revenue, 2),
            predicted_revenue=predicted_revenue,
            expected_rental_volume=self._expected_rental_volume,
            avg_revenue_per_rental=round(self._avg_revenue_per_rental, 2),
            insight=insight,
            model_metrics=self.get_model_metrics(),
            summary_statistics=self.get_summary_statistics(),
            recent_test_records=test_records,
        )

    def get_monthly_revenue(
        self, year: Optional[int] = None
    ) -> MonthlyRevenueResponse:
        """Return chronological monthly revenue timeline including historical actuals and forecast.

        Args:
            year: Optional year to filter timeline (e.g. 2024, 2025, 2026).

        Returns:
            MonthlyRevenueResponse: Timeline records and metadata.

        Raises:
            ValueError: If the requested year has no records.
        """
        # Map predictions data for O(1) lookup
        pred_map: Dict[str, Tuple[float, float, float]] = {}
        for _, row in self._predictions_df.iterrows():
            pred_map[str(row["Month"])] = (
                float(row["Predicted_Revenue"]),
                float(row["Error"]),
                float(row["Absolute_Error"]),
            )

        timeline: List[MonthlyRevenueRecord] = []

        # 1. Historical entries
        all_months = sorted(list(self._full_historical_revenue.keys()))
        for m_str in all_months:
            parts = m_str.split("-")
            yr = int(parts[0])
            mo = int(parts[1])

            if year is not None and yr != year:
                continue

            actual = float(self._full_historical_revenue[m_str])
            pred_info = pred_map.get(m_str)

            pred_rev = round(pred_info[0], 2) if pred_info else None
            err = round(pred_info[1], 2) if pred_info else None
            abs_err = round(pred_info[2], 2) if pred_info else None

            timeline.append(
                MonthlyRevenueRecord(
                    year=yr,
                    month=mo,
                    year_month=m_str,
                    historical_revenue=round(actual, 2),
                    predicted_revenue=pred_rev,
                    error=err,
                    absolute_error=abs_err,
                    is_forecast=False,
                )
            )

        # 2. Upcoming forecast entry (August 2026)
        if year is None or year == self._forecast_period.year:
            forecast_pred = round(
                self._expected_rental_volume * self._avg_revenue_per_rental, 2
            )
            timeline.append(
                MonthlyRevenueRecord(
                    year=self._forecast_period.year,
                    month=self._forecast_period.month,
                    year_month=(
                        f"{self._forecast_period.year}-{self._forecast_period.month:02d}"
                    ),
                    historical_revenue=None,
                    predicted_revenue=forecast_pred,
                    error=None,
                    absolute_error=None,
                    is_forecast=True,
                )
            )

        if not timeline:
            available_years = sorted(
                list({int(m.split("-")[0]) for m in self._full_historical_revenue.keys()})
            )
            raise ValueError(
                f"No revenue records found for year {year}. Available years: {available_years}"
            )

        return MonthlyRevenueResponse(
            forecast_period=self._forecast_period,
            filter_year=year,
            total_periods=len(timeline),
            timeline=timeline,
        )

    def get_model_comparison(self) -> RevenueModelComparisonResponse:
        """Return performance benchmark comparison across evaluated models from ML phase."""
        items: List[RevenueModelComparisonItem] = []
        for _, row in self._comparison_df.iterrows():
            r2_val = row["R2"]
            items.append(
                RevenueModelComparisonItem(
                    model=str(row["Model"]),
                    mae=round(float(row["MAE"]), 2),
                    rmse=round(float(row["RMSE"]), 2),
                    r2=round(float(r2_val), 4) if pd.notnull(r2_val) else None,
                )
            )

        rationale = (
            "The Demand-Based Revenue Forecasting approach achieved the highest validation R² "
            "(0.3740) and lowest MAE (₹142,622.32) and RMSE (₹172,030.31) on the time-aware test set. "
            "Direct regression models (Random Forest, XGBoost, Ridge) suffered severe negative R² "
            "due to strong dependency on rental volume momentum, proving that estimating revenue "
            "through expected rental volume is the most practical and accurate model."
        )

        return RevenueModelComparisonResponse(
            selected_model="Demand-Based Revenue",
            rationale=rationale,
            models=items,
        )


# Cached service instance for FastAPI dependency injection
_revenue_service_instance: Optional[RevenueService] = None


def get_revenue_service() -> RevenueService:
    """FastAPI dependency provider returning the RevenueService singleton."""
    global _revenue_service_instance
    if _revenue_service_instance is None:
        _revenue_service_instance = RevenueService()
    return _revenue_service_instance
