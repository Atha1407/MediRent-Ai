"""Unit and integration tests for the Equipment Utilisation backend module."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.utilisation_service import UtilisationService


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def service():
    """Create a standalone UtilisationService instance."""
    return UtilisationService()


def test_utilisation_service_initialization(service):
    """Test that UtilisationService initializes and precomputes all metrics."""
    assert service._raw_df is not None
    assert not service._raw_df.empty
    assert len(service.get_equipment_names()) == 16

    overall = service.get_overall_utilisation()
    assert overall is not None
    assert overall.equipment_count == 16
    assert overall.analysis_period.start_date == "2024-01-01"
    assert overall.analysis_period.end_date == "2026-07-31"
    assert overall.analysis_period.total_days == 943
    assert overall.thresholds.low_threshold_percentage in [17.82, 17.83]
    assert overall.thresholds.high_threshold_percentage in [24.18, 24.19]


def test_root_endpoint(client):
    """Test that the root health check endpoint continues to return 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "MediRent-AI API is running"}


def test_overall_utilisation_endpoint(client):
    """Test GET /api/utilisation dashboard overview endpoint."""
    response = client.get("/api/utilisation")
    assert response.status_code == 200
    data = response.json()

    # Timeframe and reference date
    assert data["analysis_period"]["start_date"] == "2024-01-01"
    assert data["analysis_period"]["end_date"] == "2026-07-31"
    assert data["analysis_period"]["total_days"] == 943
    assert data["as_of_date"] == "2026-07-31"

    # Aggregates matching authoritative notebook calculations
    assert data["average_utilisation"] == 21.08
    assert data["minimum_utilisation"] == 12.43
    assert data["maximum_utilisation"] == 31.78
    assert data["total_inventory"] == 202
    assert data["total_currently_rented"] == 102
    assert data["total_currently_available"] == 100
    assert data["total_inventory"] == data["total_currently_rented"] + data["total_currently_available"]

    # Dynamic quartile thresholds
    assert data["thresholds"]["low_threshold_percentage"] in [17.82, 17.83]
    assert data["thresholds"]["high_threshold_percentage"] in [24.18, 24.19]

    # Equipments list
    assert data["equipment_count"] == 16
    assert len(data["equipments"]) == 16

    for item in data["equipments"]:
        assert "equipment" in item
        assert "category" in item
        assert item["total_inventory"] > 0
        assert item["planned_rental_days"] >= 0
        assert item["available_equipment_days"] > 0
        assert 0.0 <= item["utilisation_percentage"] <= 100.0
        assert item["utilisation_status"] in [
            "Highly Utilised",
            "Moderately Utilised",
            "Under Utilised",
        ]
        assert item["currently_rented"] >= 0
        assert item["currently_available"] >= 0
        assert item["currently_rented"] + item["currently_available"] == item["total_inventory"]
        assert len(item["actionable_insight"]) > 0


def test_equipment_utilisation_valid(client):
    """Test GET /api/utilisation/equipment/{equipment_name} for valid equipment."""
    response = client.get("/api/utilisation/equipment/Oxygen%20Concentrator")
    assert response.status_code == 200
    data = response.json()

    assert data["equipment"] == "Oxygen Concentrator"
    assert data["category"] == "Respiratory Equipment"
    assert data["analysis_period"]["start_date"] == "2024-01-01"
    assert data["analysis_period"]["end_date"] == "2026-07-31"
    assert data["as_of_date"] == "2026-07-31"
    assert data["total_inventory"] == 16
    assert data["planned_rental_days"] == 4316.0
    assert data["available_equipment_days"] == 15088.0
    assert data["utilisation_percentage"] == 28.61
    assert data["utilisation_status"] == "Highly Utilised"
    assert data["currently_rented"] == 7
    assert data["currently_available"] == 9
    assert "Oxygen Concentrator" in data["actionable_insight"]
    assert "28.61%" in data["actionable_insight"]


def test_equipment_utilisation_case_insensitive(client):
    """Test case-insensitive resolution of equipment names."""
    for query_name in ["oxygen concentrator", "OXYGEN CONCENTRATOR", " Oxygen Concentrator "]:
        response = client.get(f"/api/utilisation/equipment/{query_name}")
        assert response.status_code == 200
        assert response.json()["equipment"] == "Oxygen Concentrator"


def test_equipment_utilisation_unknown(client):
    """Test GET /api/utilisation/equipment/{equipment_name} for non-existent equipment."""
    response = client.get("/api/utilisation/equipment/NonExistentEquipment")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "NonExistentEquipment" in detail
    assert "Available equipment:" in detail


def test_service_unknown_equipment_handling(service):
    """Test direct service response when querying an unknown equipment name."""
    detail = service.get_equipment_utilisation("NonExistentEquipment")
    assert detail is None


def test_category_utilisation_endpoint(client):
    """Test GET /api/utilisation/category ranking endpoint."""
    response = client.get("/api/utilisation/category")
    assert response.status_code == 200
    data = response.json()

    assert data["total_categories"] == 7
    assert len(data["categories"]) == 7

    # Verify ranking monotonicity and rank indexing
    ranks = [item["rank"] for item in data["categories"]]
    assert ranks == list(range(1, 8))

    util_pcts = [item["utilisation_percentage"] for item in data["categories"]]
    assert util_pcts == sorted(util_pcts, reverse=True)

    # Top category is Mobility Equipment
    top_cat = data["categories"][0]
    assert top_cat["category"] == "Mobility Equipment"
    assert top_cat["rank"] == 1
    assert top_cat["utilisation_percentage"] == 26.68
    assert top_cat["total_inventory"] == 37


def test_availability_snapshot_endpoint(client):
    """Test GET /api/utilisation/availability warehouse inventory snapshot endpoint."""
    response = client.get("/api/utilisation/availability")
    assert response.status_code == 200
    data = response.json()

    assert data["as_of_date"] == "2026-07-31"
    assert data["total_inventory"] == 202
    assert data["total_rented"] == 102
    assert data["total_available"] == 100
    assert data["equipment_count"] == 16
    assert len(data["equipments"]) == 16

    for item in data["equipments"]:
        assert item["total_inventory"] > 0
        assert item["currently_rented"] >= 0
        assert item["currently_available"] >= 0
        assert item["currently_rented"] + item["currently_available"] == item["total_inventory"]
        expected_rate = round((item["currently_available"] / item["total_inventory"]) * 100, 2)
        assert item["availability_rate_percentage"] == expected_rate


def test_utilisation_metrics_consistency(service):
    """Verify numeric validity and status classification rules across all equipment."""
    overall = service.get_overall_utilisation()
    low_th = overall.thresholds.low_threshold_percentage
    high_th = overall.thresholds.high_threshold_percentage

    for eq in overall.equipments:
        if eq.utilisation_percentage >= high_th:
            assert eq.utilisation_status == "Highly Utilised"
        elif eq.utilisation_percentage <= low_th:
            assert eq.utilisation_status == "Under Utilised"
        else:
            assert eq.utilisation_status == "Moderately Utilised"

        assert eq.currently_rented + eq.currently_available == eq.total_inventory
