"""Smart Equipment Allocation Service for MediRent-AI.

Implements the multi-criteria intelligent allocation scoring algorithm, hard constraint
enforcement, and time-aware snapshot evaluation established in
notebooks/05_Smart_Equipment_Allocation.ipynb.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.schemas.allocation import (
    AllocationMetadataResponse,
    AllocationRecommendationResponse,
    AllocationRequest,
    CandidateUnitItem,
    NextAvailableOptionItem,
)

CONDITION_SCORES: Dict[str, float] = {
    "Excellent": 100.0,
    "Good": 85.0,
    "Fair": 65.0,
    "Poor": 40.0,
}
DEFAULT_CONDITION_SCORE: float = 55.0

WEIGHTS: Dict[str, float] = {
    "Availability_Score": 0.15,
    "Condition_Score": 0.20,
    "Maintenance_Score": 0.20,
    "Availability_Window_Score": 0.15,
    "Duration_Fit_Score": 0.10,
    "Current_Utilisation_Score": 0.15,
    "Future_Demand_Score": 0.05,
}

DATE_COLUMNS = [
    "Booking_Date",
    "Rental_Start_Date",
    "Actual_Return_Date",
    "Expected_Return_Date",
    "Next_Maintenance_Due",
]


class AllocationService:
    """Service encapsulating physical unit cataloguing, availability snapshots, and suitability scoring."""

    def __init__(
        self,
        cleaned_path: Optional[Path] = None,
        demand_path: Optional[Path] = None,
        features_path: Optional[Path] = None,
    ) -> None:
        """Initialize data structures, unit catalog, and demand context from processed datasets.

        Args:
            cleaned_path: Path to cleaned medical equipment CSV.
            demand_path: Path to demand prediction CSV.
            features_path: Path to feature-engineered dataset CSV.
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        data_dir = project_root / "data" / "processed"

        self.cleaned_path = (
            cleaned_path or data_dir / "cleaned_medical_equipment_dataset.csv"
        )
        self.demand_path = (
            demand_path or data_dir / "demand_prediction_dataset.csv"
        )
        self.features_path = (
            features_path
            or data_dir / "feature_engineered_medical_equipment_dataset.csv"
        )

        self._cleaned_df = self._load_and_prepare_cleaned_data()
        self._unit_catalog = self._build_unit_catalog()
        self._demand_context = self._load_demand_context()

        # Equipment naming lookups
        raw_equipments = sorted(self._cleaned_df["Equipment"].dropna().unique())
        self._tracked_equipments: List[str] = [str(eq) for eq in raw_equipments]
        self._equipment_lookup: Dict[str, str] = {
            eq.strip().lower(): eq for eq in self._tracked_equipments
        }

    def _load_and_prepare_cleaned_data(self) -> pd.DataFrame:
        """Load and parse datetime and numeric columns for interval and snapshot calculations."""
        if not self.cleaned_path.exists():
            raise FileNotFoundError(
                f"Cleaned dataset not found at {self.cleaned_path}"
            )

        df = pd.read_csv(self.cleaned_path)

        for col in DATE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        if "Rental_Duration_Days" in df.columns:
            df["Rental_Duration_Days"] = pd.to_numeric(
                df["Rental_Duration_Days"], errors="coerce"
            )

        if "Total_Inventory" in df.columns:
            df["Total_Inventory"] = pd.to_numeric(
                df["Total_Inventory"], errors="coerce"
            )

        # Exclude cancelled rentals from active availability and intervals
        rental_status = (
            df["Rental_Status"].astype(str).str.strip().str.lower()
            if "Rental_Status" in df.columns
            else pd.Series("", index=df.index)
        )
        cancellation_status = (
            df.get("Cancellation_Status", pd.Series("", index=df.index))
            .astype(str)
            .str.strip()
            .str.lower()
        )
        df["_Is_Cancelled"] = rental_status.eq("cancelled") | (
            cancellation_status.str.contains("cancel", na=False)
            & ~cancellation_status.str.contains("not cancel", na=False)
        )

        # Build chronological interval end date
        df["Planned_End_Date"] = df["Rental_Start_Date"] + pd.to_timedelta(
            df["Rental_Duration_Days"], unit="D"
        )
        actual_ret = df["Actual_Return_Date"] if "Actual_Return_Date" in df.columns else pd.Series(pd.NaT, index=df.index)
        expected_ret = df["Expected_Return_Date"] if "Expected_Return_Date" in df.columns else pd.Series(pd.NaT, index=df.index)
        df["End_Date"] = (
            actual_ret.combine_first(expected_ret).combine_first(df["Planned_End_Date"])
        )

        return df

    def _build_unit_catalog(self) -> pd.DataFrame:
        """Extract canonical physical unit registry from rows with populated Equipment_ID."""
        known_units = (
            self._cleaned_df[self._cleaned_df["Equipment_ID"].notna()]
            .sort_values(["Equipment_ID", "Booking_Date", "Rental_Start_Date"])
            .groupby("Equipment_ID", as_index=False)
            .tail(1)
        )

        catalog_cols = [
            c
            for c in [
                "Equipment_ID",
                "Equipment",
                "Equipment_Category",
                "Total_Inventory",
                "Equipment_Age_Years",
            ]
            if c in known_units.columns
        ]

        return known_units[catalog_cols].drop_duplicates("Equipment_ID")

    def _load_demand_context(self) -> Dict[str, Tuple[float, float]]:
        """Compute future demand pressure and predicted demand per equipment using authoritative datasets."""
        source_df: Optional[pd.DataFrame] = None

        if self.demand_path.exists():
            source_df = pd.read_csv(self.demand_path)
        elif self.features_path.exists():
            source_df = pd.read_csv(self.features_path)

        demand_map: Dict[str, float] = {}
        if source_df is not None:
            proxy_candidates = [
                "Historical_Demand_Rolling_3M",
                "Historical_Demand_Lag_1",
                "Historical_Demand_Trend_2M",
                "Historical_Demand_Rolling_6M",
            ]
            chosen_col = next(
                (c for c in proxy_candidates if c in source_df.columns), None
            )
            if chosen_col:
                proxy = (
                    source_df[["Equipment", chosen_col]]
                    .dropna(subset=[chosen_col])
                    .groupby("Equipment", as_index=False)[chosen_col]
                    .last()
                )
                for _, row in proxy.iterrows():
                    demand_map[str(row["Equipment"])] = float(row[chosen_col])

        # Calculate scaled pressure across all equipment types
        values = [v for v in demand_map.values() if v > 0]
        max_demand = max(values) if values else 1.0

        context: Dict[str, Tuple[float, float]] = {}
        for eq in self._cleaned_df["Equipment"].dropna().unique():
            pred = demand_map.get(str(eq), 0.0)
            pressure = float(np.clip(pred / max_demand, 0.0, 1.0)) if max_demand > 0 else 0.0
            context[str(eq)] = (pressure, pred)

        return context

    @staticmethod
    def normalize_condition(value: Optional[str]) -> str:
        """Normalize equipment condition string."""
        if pd.isna(value) or value is None:
            return "Unknown"
        return str(value).strip().title()

    @classmethod
    def condition_score(cls, value: Optional[str]) -> float:
        """Map normalized equipment condition to score points (20% weight)."""
        norm = cls.normalize_condition(value)
        return CONDITION_SCORES.get(norm, DEFAULT_CONDITION_SCORE)

    @staticmethod
    def calculate_maintenance_score(
        maintenance_due: Optional[pd.Timestamp],
        request_start: pd.Timestamp,
        request_end: pd.Timestamp,
    ) -> float:
        """Calculate maintenance status score (20% weight)."""
        if pd.isna(maintenance_due) or maintenance_due is None:
            return 55.0

        m_due = pd.Timestamp(maintenance_due).normalize()
        r_start = pd.Timestamp(request_start).normalize()
        r_end = pd.Timestamp(request_end).normalize()

        if m_due < r_start:
            return 35.0
        if m_due < r_end:
            return 0.0

        days_after = (m_due - r_end).days
        if days_after >= 30:
            return 100.0
        return 85.0

    @staticmethod
    def calculate_duration_fit(
        maintenance_due: Optional[pd.Timestamp],
        request_start: pd.Timestamp,
        rental_duration_days: int,
    ) -> float:
        """Calculate duration fit buffer score (10% weight)."""
        if pd.isna(maintenance_due) or maintenance_due is None:
            return 60.0

        m_due = pd.Timestamp(maintenance_due).normalize()
        r_start = pd.Timestamp(request_start).normalize()
        horizon = (m_due - r_start).days

        if horizon < 0 or horizon < rental_duration_days:
            return 0.0

        extra_ratio = (horizon - rental_duration_days) / max(rental_duration_days, 1)
        return float(np.clip(70.0 + 30.0 * min(extra_ratio, 1.0), 0.0, 100.0))

    @staticmethod
    def maintenance_label(
        maintenance_due: Optional[pd.Timestamp],
        request_start: pd.Timestamp,
        request_end: pd.Timestamp,
    ) -> str:
        """Classify maintenance status into operational category."""
        if pd.isna(maintenance_due) or maintenance_due is None:
            return "Unknown"

        m_due = pd.Timestamp(maintenance_due).normalize()
        r_start = pd.Timestamp(request_start).normalize()
        r_end = pd.Timestamp(request_end).normalize()

        if m_due < r_start:
            return "Overdue"
        if m_due < r_end:
            return "Due During Rental"
        if m_due <= r_end + pd.Timedelta(days=30):
            return "Due Soon"
        return "Not Due"

    @classmethod
    def build_explanation(
        cls,
        row: pd.Series,
        request_start: pd.Timestamp,
        request_end: pd.Timestamp,
    ) -> str:
        """Construct natural language justification for the recommended unit."""
        condition = cls.normalize_condition(row.get("Equipment_Condition"))
        maint = cls.maintenance_label(
            row.get("Next_Maintenance_Due"), request_start, request_end
        )
        window = float(row.get("Availability_Window_Days", 3650.0))
        if window >= 3650.0:
            window_text = "no known upcoming booking"
        else:
            window_text = f"{int(window)} day(s) before the next known booking"

        utilisation = float(row.get("Current_Unit_Utilisation_%", 0.0))
        pressure = float(row.get("Future_Demand_Pressure", 0.0))

        if pressure >= 0.75:
            demand_text = "future demand is high, so a less-utilised unit is preferred"
        elif pressure >= 0.40:
            demand_text = "future demand is moderate"
        else:
            demand_text = "future demand pressure is relatively low"

        return (
            f"{condition} condition; maintenance status: {maint}; "
            f"{window_text}; current unit utilisation is "
            f"{utilisation:.1f}%; {demand_text}."
        )

    def build_unit_snapshot(
        self,
        reference_date: pd.Timestamp,
        exclude_rental_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """Generate point-in-time unit state snapshot as of reference date."""
        ref = pd.Timestamp(reference_date).normalize()

        known = self._cleaned_df[
            (~self._cleaned_df["_Is_Cancelled"])
            & self._cleaned_df["Equipment_ID"].notna()
            & self._cleaned_df["Booking_Date"].notna()
            & (self._cleaned_df["Booking_Date"] <= ref)
        ].copy()

        if exclude_rental_id is not None:
            known = known[
                known["Rental_ID"].astype(str) != str(exclude_rental_id)
            ].copy()

        # Latest known metadata for each physical unit up to reference date
        latest_metadata = (
            known.sort_values(
                ["Equipment_ID", "Booking_Date", "Rental_Start_Date"]
            )
            .groupby("Equipment_ID", as_index=False)
            .tail(1)
        )

        metadata_cols = [
            c
            for c in [
                "Equipment_ID",
                "Equipment_Condition",
                "Next_Maintenance_Due",
                "Equipment_Age_Years",
            ]
            if c in latest_metadata.columns
        ]

        snapshot = self._unit_catalog.merge(
            latest_metadata[metadata_cols],
            on="Equipment_ID",
            how="left",
        )

        # Active occupancy at reference date
        active = known[
            (known["Rental_Start_Date"] <= ref) & (known["End_Date"] > ref)
        ].copy()

        active_now = (
            active.sort_values("End_Date")
            .groupby("Equipment_ID", as_index=False)
            .tail(1)
        )
        active_map = active_now.set_index("Equipment_ID")

        snapshot["Currently_Rented"] = snapshot["Equipment_ID"].isin(
            active_now["Equipment_ID"]
        )
        snapshot["Current_Return_Date"] = snapshot["Equipment_ID"].map(
            active_map["End_Date"]
            if not active_map.empty
            else pd.Series(dtype="datetime64[ns]")
        )

        # Next upcoming scheduled booking known at reference date
        upcoming = known[known["Rental_Start_Date"] >= ref].copy()
        upcoming = (
            upcoming.sort_values("Rental_Start_Date")
            .groupby("Equipment_ID", as_index=False)
            .first()
        )
        upcoming_map = upcoming.set_index("Equipment_ID")

        snapshot["Next_Booked_Start"] = snapshot["Equipment_ID"].map(
            upcoming_map["Rental_Start_Date"]
            if not upcoming_map.empty
            else pd.Series(dtype="datetime64[ns]")
        )

        # Historical unit-level utilisation up to reference date
        hist = known[known["Rental_Start_Date"] < ref].copy()
        if not hist.empty:
            hist["Util_End"] = hist["End_Date"].clip(upper=ref)
            hist["Util_Start"] = hist["Rental_Start_Date"]
            hist["Rental_Days_To_Date"] = (
                hist["Util_End"] - hist["Util_Start"]
            ).dt.days.clip(lower=0)

            unit_days = hist.groupby("Equipment_ID")[
                "Rental_Days_To_Date"
            ].sum()

            min_start = self._cleaned_df["Rental_Start_Date"].min()
            obs_days = max((ref - min_start).days, 1) if pd.notna(min_start) else 1

            snapshot["Unit_Rental_Days_To_Date"] = (
                snapshot["Equipment_ID"].map(unit_days).fillna(0)
            )
            snapshot["Current_Unit_Utilisation_%"] = (
                snapshot["Unit_Rental_Days_To_Date"] / obs_days * 100.0
            ).clip(0.0, 100.0)
        else:
            snapshot["Unit_Rental_Days_To_Date"] = 0.0
            snapshot["Current_Unit_Utilisation_%"] = 0.0

        snapshot["Reference_Date"] = ref
        return snapshot

    def get_candidates(
        self,
        equipment: str,
        request_start: pd.Timestamp,
        rental_duration_days: int,
        strict_maintenance: bool = False,
        exclude_rental_id: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
        """Apply the 4 hard constraints and retrieve eligible candidate units."""
        request_start = pd.Timestamp(request_start).normalize()
        rental_duration_days = int(rental_duration_days)
        request_end = request_start + pd.Timedelta(days=rental_duration_days)

        snapshot = self.build_unit_snapshot(
            request_start, exclude_rental_id=exclude_rental_id
        )

        same_type = snapshot[snapshot["Equipment"] == equipment].copy()
        if same_type.empty:
            return pd.DataFrame(), snapshot, request_end

        # Hard constraint 2: Unit must not be currently rented at request_start
        candidates = same_type[~same_type["Currently_Rented"]].copy()
        if candidates.empty:
            return candidates, snapshot, request_end

        # Hard constraint 3: No overlapping booking during [request_start, request_end)
        known = self._cleaned_df[
            (~self._cleaned_df["_Is_Cancelled"])
            & self._cleaned_df["Equipment_ID"].notna()
            & self._cleaned_df["Booking_Date"].notna()
            & (self._cleaned_df["Booking_Date"] <= request_start)
            & (self._cleaned_df["Equipment"] == equipment)
        ].copy()

        if exclude_rental_id is not None:
            known = known[
                known["Rental_ID"].astype(str) != str(exclude_rental_id)
            ].copy()

        conflict_counts: Dict[str, int] = {}
        for eq_id, group in known.groupby("Equipment_ID"):
            overlap = (group["Rental_Start_Date"] < request_end) & (
                group["End_Date"] > request_start
            )
            conflict_counts[str(eq_id)] = int(overlap.sum())

        candidates["Known_Booking_Conflicts"] = (
            candidates["Equipment_ID"]
            .astype(str)
            .map(conflict_counts)
            .fillna(0)
            .astype(int)
        )
        candidates = candidates[candidates["Known_Booking_Conflicts"] == 0].copy()
        if candidates.empty:
            return candidates, snapshot, request_end

        # Hard constraint 4: No maintenance conflict during [request_start, request_end)
        candidates["Maintenance_Conflict"] = (
            candidates["Next_Maintenance_Due"].notna()
            & (candidates["Next_Maintenance_Due"] >= request_start)
            & (candidates["Next_Maintenance_Due"] < request_end)
        )
        candidates = candidates[~candidates["Maintenance_Conflict"]].copy()

        if strict_maintenance:
            candidates = candidates[
                candidates["Next_Maintenance_Due"].isna()
                | (candidates["Next_Maintenance_Due"] >= request_start)
            ].copy()

        if candidates.empty:
            return candidates, snapshot, request_end

        # Availability window days until next scheduled booking
        candidates["Availability_Window_Days"] = np.where(
            candidates["Next_Booked_Start"].notna(),
            (candidates["Next_Booked_Start"] - request_start).dt.days,
            3650.0,
        )

        # Demand pressure and context
        pressure, predicted_demand = self._demand_context.get(
            equipment, (0.0, np.nan)
        )
        candidates["Predicted_Future_Demand"] = predicted_demand
        candidates["Future_Demand_Pressure"] = pressure

        return candidates, snapshot, request_end

    def score_candidates(
        self,
        candidates: pd.DataFrame,
        request_start: pd.Timestamp,
        request_end: pd.Timestamp,
        rental_duration_days: int,
    ) -> pd.DataFrame:
        """Compute the composite suitability score and apply authoritative multi-level ranking."""
        if candidates.empty:
            return candidates.copy()

        scored = candidates.copy()

        # 1. Availability Score: 15%
        scored["Availability_Score"] = 100.0

        # 2. Condition Score: 20%
        scored["Condition_Score"] = scored["Equipment_Condition"].apply(
            self.condition_score
        )

        # 3. Maintenance Score: 20%
        scored["Maintenance_Score"] = scored.apply(
            lambda r: self.calculate_maintenance_score(
                r["Next_Maintenance_Due"], request_start, request_end
            ),
            axis=1,
        )

        # 4. Availability Window Score: 15%
        window_ratio = scored["Availability_Window_Days"] / max(
            3 * rental_duration_days, 1
        )
        scored["Availability_Window_Score"] = np.minimum(
            100.0, 40.0 + 60.0 * np.minimum(window_ratio, 1.0)
        )

        # 5. Duration Fit Score: 10%
        scored["Duration_Fit_Score"] = scored.apply(
            lambda r: self.calculate_duration_fit(
                r["Next_Maintenance_Due"], request_start, rental_duration_days
            ),
            axis=1,
        )

        # 6. Current Utilisation Score: 15%
        base_util = (
            100.0 - scored["Current_Unit_Utilisation_%"].fillna(0.0)
        ).clip(0.0, 100.0)
        multiplier = 1.0 + 0.50 * scored["Future_Demand_Pressure"].fillna(0.0)
        scored["Current_Utilisation_Score"] = np.minimum(
            100.0, base_util * multiplier
        )

        # 7. Future Demand Score: 5%
        scored["Future_Demand_Score"] = 100.0 * (
            1.0 - scored["Future_Demand_Pressure"].fillna(0.0)
        )

        # Composite Suitability Score: sum of weights
        scored["Suitability_Score"] = 0.0
        for comp, weight in WEIGHTS.items():
            scored["Suitability_Score"] += scored[comp] * weight

        scored["Suitability_Score"] = (
            scored["Suitability_Score"].clip(0.0, 100.0).round(2)
        )

        # Authoritative ranking order:
        # 1. Suitability descending
        # 2. Condition descending
        # 3. Maintenance descending
        # 4. Availability Window Days descending
        # 5. Current Unit Utilisation ascending
        scored = scored.sort_values(
            [
                "Suitability_Score",
                "Condition_Score",
                "Maintenance_Score",
                "Availability_Window_Days",
                "Current_Unit_Utilisation_%",
            ],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)

        scored["Rank"] = np.arange(1, len(scored) + 1)
        return scored

    def next_available_options(
        self,
        equipment: str,
        request_start: pd.Timestamp,
        exclude_rental_id: Optional[str] = None,
    ) -> List[NextAvailableOptionItem]:
        """Generate soonest availability options when no candidate satisfies immediate criteria."""
        snapshot = self.build_unit_snapshot(
            request_start, exclude_rental_id=exclude_rental_id
        )

        options = snapshot[snapshot["Equipment"] == equipment].copy()
        if options.empty:
            return []

        options["Expected_Available_Date"] = np.where(
            options["Currently_Rented"],
            options["Current_Return_Date"],
            pd.Timestamp(request_start),
        )
        options["Expected_Available_Date"] = pd.to_datetime(
            options["Expected_Available_Date"], errors="coerce"
        )

        options = options.sort_values(
            ["Expected_Available_Date", "Equipment_ID"], ascending=[True, True]
        ).head(5)

        items: List[NextAvailableOptionItem] = []
        for _, row in options.iterrows():
            ret_str = (
                row["Current_Return_Date"].strftime("%Y-%m-%d")
                if pd.notna(row["Current_Return_Date"])
                else None
            )
            avail_str = (
                row["Expected_Available_Date"].strftime("%Y-%m-%d")
                if pd.notna(row["Expected_Available_Date"])
                else None
            )
            items.append(
                NextAvailableOptionItem(
                    equipment_id=str(row["Equipment_ID"]),
                    equipment=str(row["Equipment"]),
                    condition=self.normalize_condition(
                        row.get("Equipment_Condition")
                    ),
                    current_return_date=ret_str,
                    expected_available_date=avail_str,
                )
            )
        return items

    def recommend_equipment(
        self, request: AllocationRequest
    ) -> AllocationRecommendationResponse:
        """Process customer request and generate optimal equipment recommendation."""
        # 1. Canonical equipment name resolution
        cleaned_eq = request.equipment.strip().lower()
        canonical_eq = self._equipment_lookup.get(cleaned_eq)
        if canonical_eq is None:
            raise ValueError(
                f"Equipment '{request.equipment}' not found. "
                f"Available equipment: {self._tracked_equipments}"
            )

        # 2. Date parsing
        try:
            request_start = pd.Timestamp(request.request_start).normalize()
        except Exception as exc:
            raise ValueError(
                f"Invalid request_start date '{request.request_start}': {exc}"
            ) from exc

        # 3. Retrieve candidates satisfying hard constraints
        candidates, snapshot, request_end = self.get_candidates(
            equipment=canonical_eq,
            request_start=request_start,
            rental_duration_days=request.rental_duration_days,
            strict_maintenance=request.strict_maintenance,
            exclude_rental_id=request.exclude_rental_id,
        )

        start_str = request_start.strftime("%Y-%m-%d")
        end_str = request_end.strftime("%Y-%m-%d")

        # 4. Handle no suitable unit scenario
        if candidates.empty:
            next_opts = self.next_available_options(
                equipment=canonical_eq,
                request_start=request_start,
                exclude_rental_id=request.exclude_rental_id,
            )
            status_text = "No suitable unit currently available"
            reason_text = (
                "No unit satisfies the current availability "
                "and maintenance-period constraints."
            )
            return AllocationRecommendationResponse(
                recommendation_status=status_text,
                equipment=canonical_eq,
                request_start_date=start_str,
                request_end_date=end_str,
                rental_duration_days=request.rental_duration_days,
                recommended_equipment_id=None,
                suitability_score=None,
                condition=None,
                maintenance_status=None,
                availability_window_days=None,
                current_unit_utilisation_percentage=None,
                current_unit_utilisation_pct=None,
                predicted_future_demand=None,
                reason=reason_text,
                candidates=[],
                next_available_options=next_opts,
                # Title-cased aliases
                Recommendation_Status=status_text,
                Recommended_Equipment_ID=None,
                Suitability_Score=None,
                Condition=None,
                Maintenance_Status=None,
                Availability_Window_Days=None,
                Reason=reason_text,
            )

        # 5. Score and rank candidates
        scored = self.score_candidates(
            candidates,
            request_start=request_start,
            request_end=request_end,
            rental_duration_days=request.rental_duration_days,
        )

        best = scored.iloc[0]
        best_id = str(best["Equipment_ID"])
        best_score = float(best["Suitability_Score"])
        best_cond = self.normalize_condition(best.get("Equipment_Condition"))
        best_maint = self.maintenance_label(
            best.get("Next_Maintenance_Due"), request_start, request_end
        )
        best_window = float(best["Availability_Window_Days"])
        best_util = float(round(best["Current_Unit_Utilisation_%"], 2))
        best_pred = (
            float(round(best["Predicted_Future_Demand"], 2))
            if pd.notna(best.get("Predicted_Future_Demand"))
            else None
        )
        explanation = self.build_explanation(
            best, request_start=request_start, request_end=request_end
        )

        candidate_items: List[CandidateUnitItem] = []
        for _, row in scored.iterrows():
            booked_str = (
                row["Next_Booked_Start"].strftime("%Y-%m-%d")
                if pd.notna(row.get("Next_Booked_Start"))
                else None
            )
            maint_str = (
                row["Next_Maintenance_Due"].strftime("%Y-%m-%d")
                if pd.notna(row.get("Next_Maintenance_Due"))
                else None
            )
            u_pct = float(round(row["Current_Unit_Utilisation_%"], 2))
            candidate_items.append(
                CandidateUnitItem(
                    rank=int(row["Rank"]),
                    equipment_id=str(row["Equipment_ID"]),
                    equipment=canonical_eq,
                    condition=self.normalize_condition(
                        row.get("Equipment_Condition")
                    ),
                    equipment_condition=str(row.get("Equipment_Condition", "")),
                    suitability_score=float(row["Suitability_Score"]),
                    availability_score=float(row["Availability_Score"]),
                    condition_score=float(row["Condition_Score"]),
                    maintenance_score=float(row["Maintenance_Score"]),
                    availability_window_score=float(
                        row["Availability_Window_Score"]
                    ),
                    duration_fit_score=float(row["Duration_Fit_Score"]),
                    current_utilisation_score=float(
                        row["Current_Utilisation_Score"]
                    ),
                    future_demand_score=float(row["Future_Demand_Score"]),
                    current_unit_utilisation_percentage=u_pct,
                    current_unit_utilisation_pct=u_pct,
                    availability_window_days=float(
                        row["Availability_Window_Days"]
                    ),
                    next_booked_start=booked_str,
                    next_maintenance_due=maint_str,
                )
            )

        status_rec = "Recommended"
        return AllocationRecommendationResponse(
            recommendation_status=status_rec,
            equipment=canonical_eq,
            request_start_date=start_str,
            request_end_date=end_str,
            rental_duration_days=request.rental_duration_days,
            recommended_equipment_id=best_id,
            suitability_score=best_score,
            condition=best_cond,
            maintenance_status=best_maint,
            availability_window_days=best_window,
            current_unit_utilisation_percentage=best_util,
            current_unit_utilisation_pct=best_util,
            predicted_future_demand=best_pred,
            reason=explanation,
            candidates=candidate_items,
            next_available_options=[],
            # Title-cased aliases
            Recommendation_Status=status_rec,
            Recommended_Equipment_ID=best_id,
            Suitability_Score=best_score,
            Condition=best_cond,
            Maintenance_Status=best_maint,
            Availability_Window_Days=best_window,
            Reason=explanation,
        )

    def get_tracked_equipment(self) -> List[str]:
        """Return list of canonical medical equipment types."""
        return self._tracked_equipments

    def get_metadata(self) -> AllocationMetadataResponse:
        """Return operational metadata and scoring policy config."""
        return AllocationMetadataResponse(
            status="operational",
            total_units=len(self._unit_catalog),
            total_equipment_types=len(self._tracked_equipments),
            weights=WEIGHTS,
            default_strict_maintenance=False,
            equipment_list=self._tracked_equipments,
        )


# Cached singleton instance for FastAPI dependency injection
_allocation_service_instance: Optional[AllocationService] = None


def get_allocation_service() -> AllocationService:
    """FastAPI dependency provider returning the AllocationService singleton."""
    global _allocation_service_instance
    if _allocation_service_instance is None:
        _allocation_service_instance = AllocationService()
    return _allocation_service_instance
