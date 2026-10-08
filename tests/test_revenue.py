"""Unit and integration tests for the Revenue Prediction backend module."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.revenue_service import RevenueService


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def service():
    """Create a standalone RevenueService instance."""
    return RevenueService()


def test_root_endpoint(client):
    """Test that GET / still returns the running health message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "MediRent-AI API is running"}


def test_revenue_overview(client):
    """Test the GET /api/revenue overview endpoint."""
    response = client.get("/api/revenue")
    assert response.status_code == 200
    data = response.json()

    # Forecast period
    assert data["forecast_period"]["year"] == 2026
    assert data["forecast_period"]["month"] == 8
    assert data["forecast_period"]["label"] == "August 2026"

    # Latest historical observation
    assert data["latest_historical_period"]["year"] == 2026
    assert data["latest_historical_period"]["month"] == 7
    assert data["latest_historical_period"]["label"] == "July 2026"
    assert data["latest_historical_revenue"] == 989370.0

    # Predicted revenue and drivers
    assert round(data["predicted_revenue"], 2) == 988085.43
    assert data["expected_rental_volume"] == 236.0
    assert round(data["avg_revenue_per_rental"], 2) == 4186.80
    assert "August 2026" in data["insight"]

    # Model metrics
    metrics = data["model_metrics"]
    assert metrics["model_name"] == "Demand-Based Revenue Forecasting"
    assert metrics["mae"] == 142622.32
    assert metrics["rmse"] == 172030.31
    assert metrics["r2"] == 0.3740
    assert metrics["test_period"] == "December 2025 - July 2026"

    # Summary statistics and test records
    assert data["summary_statistics"]["total_historical_months"] >= 8
    assert len(data["recent_test_records"]) == 8


def test_monthly_revenue_timeline(client):
    """Test GET /api/revenue/monthly chronological timeline."""
    response = client.get("/api/revenue/monthly")
    assert response.status_code == 200
    data = response.json()

    assert data["forecast_period"]["year"] == 2026
    assert data["forecast_period"]["month"] == 8
    assert data["total_periods"] >= 9
    assert len(data["timeline"]) == data["total_periods"]

    # Check future forecast entry
    forecast_entry = data["timeline"][-1]
    assert forecast_entry["year_month"] == "2026-08"
    assert forecast_entry["is_forecast"] is True
    assert forecast_entry["historical_revenue"] is None
    assert round(forecast_entry["predicted_revenue"], 2) == 988085.43

    # Check a test validation record (July 2026)
    jul_entry = [e for e in data["timeline"] if e["year_month"] == "2026-07"][0]
    assert jul_entry["is_forecast"] is False
    assert jul_entry["historical_revenue"] == 989370.0
    assert round(jul_entry["predicted_revenue"], 2) == 820613.32


def test_monthly_revenue_filtered_year(client):
    """Test GET /api/revenue/monthly with a valid year filter."""
    response = client.get("/api/revenue/monthly?year=2026")
    assert response.status_code == 200
    data = response.json()

    assert data["filter_year"] == 2026
    # 7 historical months in 2026 + 1 forecast month in 2026
    assert data["total_periods"] == 8
    for item in data["timeline"]:
        assert item["year"] == 2026


def test_monthly_revenue_invalid_year(client):
    """Test GET /api/revenue/monthly with an invalid year returns 404."""
    response = client.get("/api/revenue/monthly?year=1999")
    assert response.status_code == 404
    assert "1999" in response.json()["detail"]


def test_revenue_model_comparison(client):
    """Test GET /api/revenue/comparison benchmarks."""
    response = client.get("/api/revenue/comparison")
    assert response.status_code == 200
    data = response.json()

    assert data["selected_model"] == "Demand-Based Revenue"
    assert len(data["models"]) == 5

    models_dict = {m["model"]: m for m in data["models"]}
    assert "Demand-Based Revenue" in models_dict
    assert "Previous-Month Revenue" in models_dict
    assert "Random Forest" in models_dict
    assert "XGBoost" in models_dict
    assert "Ridge" in models_dict

    demand_based = models_dict["Demand-Based Revenue"]
    assert demand_based["mae"] == 142622.32
    assert demand_based["rmse"] == 172030.31
    assert demand_based["r2"] == 0.3740
