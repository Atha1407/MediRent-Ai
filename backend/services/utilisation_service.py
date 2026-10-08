"""Equipment Utilisation Service for MediRent-AI.

Implements the authoritative pool-level utilisation methodology, dynamic quartile
classification, and current inventory availability snapshots established in
notebooks/05_Equipment_Utilisation_Updated.ipynb.
"""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from backend.schemas.utilisation import (
    AnalysisPeriod,
    AvailabilitySnapshotResponse,
    CategoryUtilisationItem,
    CategoryUtilisationResponse,
    EquipmentAvailabilityItem,
    EquipmentUtilisationDetailResponse,
    EquipmentUtilisationItem,
    OverallUtilisationResponse,
    UtilisationThresholds,
)

REQUIRED_DATASET_COLUMNS = {
    "Equipment",
    "Equipment_Category",
    "Rental_Start_Date",
    "Rental_Duration_Days",
    "Rental_Status",
    "Total_Inventory",
}

DEFAULT_SNAPSHOT_DATE = pd.Timestamp("2026-07-31")


class UtilisationService:
    """Service encapsulating equipment utilisation calculations, category rankings, and availability."""

    def __init__(self, dataset_path: Optional[Path] = None) -> None:
        """Initialize and precompute utilisation metrics from the processed dataset.

        Args:
            dataset_path: Path to dataset CSV. Defaults to feature engineered dataset path.
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        self.dataset_path = (
            dataset_path
            or project_root
            / "data"
            / "processed"
            / "feature_engineered_medical_equipment_dataset.csv"
        )
        self.fallback_path = (
            project_root
            / "data"
            / "processed"
            / "cleaned_medical_equipment_dataset.csv"
        )

        self._raw_df = self._load_and_validate_dataset()

        # In-memory cached responses
        self._equipment_items: List[EquipmentUtilisationItem] = []
        self._equipment_lookup: Dict[str, EquipmentUtilisationItem] = {}
        self._category_items: List[CategoryUtilisationItem] = []
        self._availability_items: List[EquipmentAvailabilityItem] = []
        self._overall_response: Optional[OverallUtilisationResponse] = None

        self._calculate_all()

    def _load_and_validate_dataset(self) -> pd.DataFrame:
        """Load and validate the dataset, attempting primary and fallback paths."""
        path_to_use = self.dataset_path
        if not path_to_use.exists():
            path_to_use = self.fallback_path
            if not path_to_use.exists():
                raise FileNotFoundError(
                    f"Neither primary ({self.dataset_path}) nor fallback ({self.fallback_path}) dataset was found."
                )

        df = pd.read_csv(path_to_use)

        missing = REQUIRED_DATASET_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"Utilisation dataset is missing required columns: {sorted(missing)}"
            )

        if df.empty:
            raise ValueError("Utilisation dataset is empty.")

        return df

    @staticmethod
    def _generate_insight(
        equipment: str,
        status: str,
        utilisation_pct: float,
        currently_available: int,
    ) -> str:
        """Generate actionable natural language interpretation of utilisation and availability."""
        if status == "Highly Utilised":
            return (
                f"{equipment} has high utilisation ({utilisation_pct:.2f}%) "
                f"and {currently_available} unit(s) currently available."
            )
        elif status == "Under Utilised":
            return (
                f"{equipment} is under-utilised ({utilisation_pct:.2f}%) "
                f"with {currently_available} unit(s) currently available."
            )
        else:
            return (
                f"{equipment} has moderate utilisation ({utilisation_pct:.2f}%) "
                f"and {currently_available} unit(s) currently available."
            )

    def _calculate_all(self) -> None:
        """Execute the exact calculation pipeline from the source notebook and cache results."""
        df = self._raw_df.copy()
        df["Rental_Start_Date"] = pd.to_datetime(
            df["Rental_Start_Date"], errors="coerce"
        )

        # 1. Exclude cancelled rentals
        util_df = df[df["Rental_Status"] != "Cancelled"].copy()
        util_df["Rental_End_Date"] = util_df["Rental_Start_Date"] + pd.to_timedelta(
            util_df["Rental_Duration_Days"], unit="D"
        )

        # 2. Define authoritative analysis window
        analysis_start = util_df["Rental_Start_Date"].min().normalize()
        analysis_end = DEFAULT_SNAPSHOT_DATE
        analysis_days = (analysis_end - analysis_start).days + 1

        self._analysis_period = AnalysisPeriod(
            start_date=analysis_start.strftime("%Y-%m-%d"),
            end_date=analysis_end.strftime("%Y-%m-%d"),
            total_days=int(analysis_days),
        )

        # 3. Clip rental periods to the analysis window
        util_df["Utilisation_Start"] = util_df["Rental_Start_Date"].clip(
            lower=analysis_start, upper=analysis_end
        )
        util_df["Utilisation_End"] = util_df["Rental_End_Date"].clip(
            lower=analysis_start + pd.Timedelta(days=1),
            upper=analysis_end + pd.Timedelta(days=1),
        )
        util_df["Rental_Days_Within_Analysis"] = (
            util_df["Utilisation_End"] - util_df["Utilisation_Start"]
        ).dt.days.clip(lower=0)

        # 4. Inventory and planned rental days
        equipment_inventory = (
            util_df.groupby(
                ["Equipment", "Equipment_Category"], as_index=False
            )["Total_Inventory"]
            .first()
            .sort_values("Equipment")
        )

        equipment_rental_days = (
            util_df.groupby("Equipment", as_index=False)[
                "Rental_Days_Within_Analysis"
            ]
            .sum()
            .rename(
                columns={"Rental_Days_Within_Analysis": "Planned_Rental_Days"}
            )
        )

        eq_util = equipment_inventory.merge(
            equipment_rental_days, on="Equipment", how="left"
        )
        eq_util["Planned_Rental_Days"] = eq_util["Planned_Rental_Days"].fillna(0)
        eq_util["Available_Equipment_Days"] = (
            eq_util["Total_Inventory"] * analysis_days
        )
        eq_util["Utilisation_%"] = (
            (eq_util["Planned_Rental_Days"] / eq_util["Available_Equipment_Days"])
            * 100
        ).round(2)

        # 5. Dynamic quartile thresholds
        low_th = float(eq_util["Utilisation_%"].quantile(0.25))
        high_th = float(eq_util["Utilisation_%"].quantile(0.75))
        self._thresholds = UtilisationThresholds(
            low_threshold_percentage=round(low_th, 2),
            high_threshold_percentage=round(high_th, 2),
        )

        def classify_status(val: float) -> str:
            if val >= high_th:
                return "Highly Utilised"
            elif val <= low_th:
                return "Under Utilised"
            else:
                return "Moderately Utilised"

        eq_util["Utilisation_Status"] = eq_util["Utilisation_%"].apply(
            classify_status
        )

        # 6. Current availability snapshot as of 2026-07-31
        current_rentals = util_df[
            (util_df["Rental_Start_Date"] <= DEFAULT_SNAPSHOT_DATE)
            & (util_df["Rental_End_Date"] > DEFAULT_SNAPSHOT_DATE)
        ].copy()

        current_rented = (
            current_rentals.groupby("Equipment")
            .size()
            .reset_index(name="Currently_Rented")
        )

        current_avail = equipment_inventory.merge(
            current_rented, on="Equipment", how="left"
        )
        current_avail["Currently_Rented"] = (
            current_avail["Currently_Rented"].fillna(0).astype(int)
        )
        current_avail["Currently_Available"] = (
            current_avail["Total_Inventory"] - current_avail["Currently_Rented"]
        )

        # Merge availability into equipment utilisation
        final_df = eq_util.merge(
            current_avail[["Equipment", "Currently_Rented", "Currently_Available"]],
            on="Equipment",
            how="left",
        )

        # Build equipment items and lookup dictionary
        self._equipment_items = []
        self._equipment_lookup = {}
        self._availability_items = []

        for _, row in final_df.iterrows():
            eq_name = str(row["Equipment"])
            cat_name = str(row["Equipment_Category"])
            tot_inv = int(row["Total_Inventory"])
            planned_days = float(row["Planned_Rental_Days"])
            avail_days = float(row["Available_Equipment_Days"])
            util_pct = float(row["Utilisation_%"])
            status = str(row["Utilisation_Status"])
            rented = int(row["Currently_Rented"])
            available = int(row["Currently_Available"])

            insight = self._generate_insight(
                eq_name, status, util_pct, available
            )

            item = EquipmentUtilisationItem(
                equipment=eq_name,
                category=cat_name,
                total_inventory=tot_inv,
                planned_rental_days=planned_days,
                available_equipment_days=avail_days,
                utilisation_percentage=util_pct,
                utilisation_status=status,
                currently_rented=rented,
                currently_available=available,
                actionable_insight=insight,
            )

            self._equipment_items.append(item)
            self._equipment_lookup[eq_name.strip().lower()] = item

            # Availability item
            avail_rate = (
                round((available / tot_inv) * 100, 2) if tot_inv > 0 else 0.0
            )
            self._availability_items.append(
                EquipmentAvailabilityItem(
                    equipment=eq_name,
                    category=cat_name,
                    total_inventory=tot_inv,
                    currently_rented=rented,
                    currently_available=available,
                    availability_rate_percentage=avail_rate,
                )
            )

        # 7. Category-wise utilisation ranking
        cat_df = (
            eq_util.groupby("Equipment_Category", as_index=False)
            .agg(
                Planned_Rental_Days=("Planned_Rental_Days", "sum"),
                Available_Equipment_Days=("Available_Equipment_Days", "sum"),
                Total_Inventory=("Total_Inventory", "sum"),
            )
        )
        cat_df["Utilisation_%"] = (
            (cat_df["Planned_Rental_Days"] / cat_df["Available_Equipment_Days"])
            * 100
        ).round(2)
        cat_df = cat_df.sort_values("Utilisation_%", ascending=False).reset_index(
            drop=True
        )

        self._category_items = [
            CategoryUtilisationItem(
                category=str(row["Equipment_Category"]),
                planned_rental_days=float(row["Planned_Rental_Days"]),
                available_equipment_days=float(row["Available_Equipment_Days"]),
                total_inventory=int(row["Total_Inventory"]),
                utilisation_percentage=float(row["Utilisation_%"]),
                rank=idx + 1,
            )
            for idx, row in cat_df.iterrows()
        ]

        # 8. Overall response caching
        u_vals = [item.utilisation_percentage for item in self._equipment_items]
        self._overall_response = OverallUtilisationResponse(
            analysis_period=self._analysis_period,
            as_of_date=DEFAULT_SNAPSHOT_DATE.strftime("%Y-%m-%d"),
            average_utilisation=round(sum(u_vals) / len(u_vals), 2),
            minimum_utilisation=min(u_vals),
            maximum_utilisation=max(u_vals),
            total_inventory=sum(item.total_inventory for item in self._equipment_items),
            total_currently_rented=sum(
                item.currently_rented for item in self._equipment_items
            ),
            total_currently_available=sum(
                item.currently_available for item in self._equipment_items
            ),
            thresholds=self._thresholds,
            equipment_count=len(self._equipment_items),
            equipments=self._equipment_items,
        )

    def get_overall_utilisation(self) -> OverallUtilisationResponse:
        """Return overall aggregate utilisation dashboard response."""
        return self._overall_response

    def get_equipment_utilisation(
        self, equipment_name: str
    ) -> Optional[EquipmentUtilisationDetailResponse]:
        """Return utilisation detail for a single equipment type (case-insensitive)."""
        cleaned = equipment_name.strip().lower()
        item = self._equipment_lookup.get(cleaned)
        if item is None:
            return None

        return EquipmentUtilisationDetailResponse(
            equipment=item.equipment,
            category=item.category,
            analysis_period=self._analysis_period,
            as_of_date=DEFAULT_SNAPSHOT_DATE.strftime("%Y-%m-%d"),
            total_inventory=item.total_inventory,
            planned_rental_days=item.planned_rental_days,
            available_equipment_days=item.available_equipment_days,
            utilisation_percentage=item.utilisation_percentage,
            utilisation_status=item.utilisation_status,
            currently_rented=item.currently_rented,
            currently_available=item.currently_available,
            actionable_insight=item.actionable_insight,
        )

    def get_category_utilisation(self) -> CategoryUtilisationResponse:
        """Return category-wise utilisation ranking response."""
        return CategoryUtilisationResponse(
            total_categories=len(self._category_items),
            categories=self._category_items,
        )

    def get_availability_snapshot(self) -> AvailabilitySnapshotResponse:
        """Return current inventory availability snapshot."""
        return AvailabilitySnapshotResponse(
            as_of_date=DEFAULT_SNAPSHOT_DATE.strftime("%Y-%m-%d"),
            total_inventory=self._overall_response.total_inventory,
            total_rented=self._overall_response.total_currently_rented,
            total_available=self._overall_response.total_currently_available,
            equipment_count=self._overall_response.equipment_count,
            equipments=self._availability_items,
        )

    def get_equipment_names(self) -> List[str]:
        """Return list of valid canonical equipment names."""
        return [item.equipment for item in self._equipment_items]


# Cached service instance for FastAPI dependency injection
_utilisation_service_instance: Optional[UtilisationService] = None


def get_utilisation_service() -> UtilisationService:
    """FastAPI dependency provider returning the UtilisationService singleton."""
    global _utilisation_service_instance
    if _utilisation_service_instance is None:
        _utilisation_service_instance = UtilisationService()
    return _utilisation_service_instance
