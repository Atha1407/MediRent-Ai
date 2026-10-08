"""Unit and integration tests for the Demand Prediction backend module."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.demand_service import DemandService


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def service():
    """Create a standalone DemandService instance."""
    return DemandService()


def test_root_endpoint(client):
    """Test that the existing GET / endpoint still works as expected."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "MediRent-AI API is running"}


def test_demand_overview(client):
    """Test the GET /api/demand overview endpoint."""
    response = client.get("/api/demand")
    assert response.status_code == 200
    data = response.json()

    assert data["forecast_period"]["year"] == 2026
    assert data["forecast_period"]["month"] == 8
    assert data["forecast_period"]["label"] == "August 2026"
    assert data["total_predicted_demand"] == 236.0
    assert data["equipment_count"] == 16
    assert len(data["equipments"]) == 16

    # Verify model metrics
    metrics = data["model_metrics"]
    assert metrics["model_name"] == "Previous-Month Demand Baseline"
    assert round(metrics["mae"], 2) == 4.59
    assert round(metrics["rmse"], 2) == 5.89
    assert round(metrics["r2"], 2) == 0.46


def test_equipment_detail_valid(client):
    """Test GET /api/demand/equipment/{equipment_name} for a valid equipment."""
    response = client.get("/api/demand/equipment/Oxygen Concentrator")
    assert response.status_code == 200
    data = response.json()

    assert data["equipment"] == "Oxygen Concentrator"
    assert data["category"] == "Respiratory Equipment"
    assert data["latest_actual_demand"] == 17.0
    assert data["predicted_demand"] == 17.0
    assert data["trend"] == "decreasing"
    assert "Oxygen Concentrator" in data["insight"]
    assert data["summary"]["total_months"] == 31
    assert len(data["history"]) == 31


def test_equipment_detail_case_insensitive(client):
    """Test case-insensitive resolution of equipment name."""
    response = client.get("/api/demand/equipment/oxygen concentrator")
    assert response.status_code == 200
    assert response.json()["equipment"] == "Oxygen Concentrator"


def test_equipment_detail_invalid(client):
    """Test that an invalid equipment name returns 404."""
    response = client.get("/api/demand/equipment/NonExistentItem")
    assert response.status_code == 404
    assert "NonExistentItem" in response.json()["detail"]


def test_monthly_demand(client):
    """Test GET /api/demand/monthly aggregated timeline."""
    response = client.get("/api/demand/monthly")
    assert response.status_code == 200
    data = response.json()

    assert data["total_periods"] == 32
    assert data["timeline"][0]["year_month"] == "2024-01"
    assert data["timeline"][0]["total_actual_demand"] == 70.0
    assert data["timeline"][0]["total_predicted_demand"] is None

    forecast_record = data["timeline"][-1]
    assert forecast_record["year_month"] == "2026-08"
    assert forecast_record["is_forecast"] is True
    assert forecast_record["total_actual_demand"] is None
    assert forecast_record["total_predicted_demand"] == 236.0


def test_monthly_demand_filtered(client):
    """Test GET /api/demand/monthly filtered by equipment."""
    response = client.get("/api/demand/monthly?equipment=BiPAP Machine")
    assert response.status_code == 200
    data = response.json()

    assert data["filter_equipment"] == "BiPAP Machine"
    assert data["total_periods"] == 32
    # BiPAP Machine demand in July 2026 was 15
    assert data["timeline"][-1]["total_predicted_demand"] == 15.0


def test_monthly_demand_invalid_filter(client):
    """Test GET /api/demand/monthly with invalid equipment filter returns 404."""
    response = client.get("/api/demand/monthly?equipment=InvalidItem")
    assert response.status_code == 404


def test_model_comparison(client):
    """Test GET /api/demand/comparison benchmarks."""
    response = client.get("/api/demand/comparison")
    assert response.status_code == 200
    data = response.json()

    assert data["selected_model"] == "Previous-Month Baseline"
    assert len(data["models"]) == 3
    model_names = [m["model"] for m in data["models"]]
    assert "Previous-Month Baseline" in model_names


def test_list_equipments(client):
    """Test GET /api/demand/equipments listing."""
    response = client.get("/api/demand/equipments")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 16
    eq_names = [item["equipment"] for item in data]
    assert "Oxygen Concentrator" in eq_names
