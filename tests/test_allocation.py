"""Unit and integration tests for the Smart Equipment Allocation backend module."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.allocation_service import AllocationService


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def service():
    """Create a standalone AllocationService instance."""
    return AllocationService()


def test_allocation_service_initialization(service):
    """Test that AllocationService initializes unit catalog, tracked equipment, and demand context."""
    assert service._cleaned_df is not None
    assert not service._cleaned_df.empty
    assert len(service._unit_catalog) == 202
    assert len(service.get_tracked_equipment()) == 16
    assert "Oxygen Concentrator" in service.get_tracked_equipment()

    metadata = service.get_metadata()
    assert metadata.status == "operational"
    assert metadata.total_units == 202
    assert metadata.total_equipment_types == 16
    assert len(metadata.weights) == 7
    assert round(sum(metadata.weights.values()), 2) == 1.0


def test_allocation_metadata_endpoint(client):
    """Test GET /api/allocation metadata and policy configuration endpoint."""
    response = client.get("/api/allocation")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "operational"
    assert data["total_units"] == 202
    assert data["total_equipment_types"] == 16
    assert len(data["equipment_list"]) == 16
    assert data["weights"]["Availability_Score"] == 0.15
    assert data["weights"]["Condition_Score"] == 0.20
    assert data["weights"]["Maintenance_Score"] == 0.20
    assert data["weights"]["Availability_Window_Score"] == 0.15
    assert data["weights"]["Duration_Fit_Score"] == 0.10
    assert data["weights"]["Current_Utilisation_Score"] == 0.15
    assert data["weights"]["Future_Demand_Score"] == 0.05


def test_valid_allocation_request(client):
    """Test POST /api/allocation/recommend with authoritative demo request."""
    payload = {
        "equipment": "Oxygen Concentrator",
        "rental_duration_days": 12,
        "request_start": "2026-07-31",
    }
    response = client.post("/api/allocation/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Core recommendation metrics matching notebook demo
    assert data["recommendation_status"] == "Recommended"
    assert data["equipment"] == "Oxygen Concentrator"
    assert data["request_start_date"] == "2026-07-31"
    assert data["request_end_date"] == "2026-08-12"
    assert data["rental_duration_days"] == 12
    assert data["recommended_equipment_id"] == "OC-014"
    assert round(data["suitability_score"], 2) == 92.38
    assert data["condition"] == "Good"
    assert data["maintenance_status"] == "Not Due"
    assert data["availability_window_days"] == 3650.0
    assert round(data["current_unit_utilisation_percentage"], 2) == 24.63
    assert round(data["predicted_future_demand"], 2) == 24.33
    assert "Good condition" in data["reason"]

    # Candidate units list
    assert len(data["candidates"]) == 9
    top = data["candidates"][0]
    assert top["rank"] == 1
    assert top["equipment_id"] == "OC-014"
    assert top["condition"] == "Good"
    assert round(top["suitability_score"], 2) == 92.38
    assert top["maintenance_score"] == 100.0

    # No fallback options required when recommended
    assert len(data["next_available_options"]) == 0


def test_case_insensitive_equipment_lookup(client):
    """Test case-insensitive resolution of equipment name in allocation request."""
    payload = {
        "equipment": "oxygen concentrator",
        "rental_duration_days": 12,
        "request_start": "2026-07-31",
    }
    response = client.post("/api/allocation/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["equipment"] == "Oxygen Concentrator"
    assert data["recommended_equipment_id"] == "OC-014"


def test_missing_required_inputs(client):
    """Test that missing required fields return 422 Unprocessable Entity."""
    # Empty body
    res1 = client.post("/api/allocation/recommend", json={})
    assert res1.status_code == 422

    # Missing duration
    res2 = client.post(
        "/api/allocation/recommend",
        json={"equipment": "Oxygen Concentrator", "request_start": "2026-07-31"},
    )
    assert res2.status_code == 422

    # Missing equipment
    res3 = client.post(
        "/api/allocation/recommend",
        json={"rental_duration_days": 5, "request_start": "2026-07-31"},
    )
    assert res3.status_code == 422

    # Missing start date
    res4 = client.post(
        "/api/allocation/recommend",
        json={"equipment": "Oxygen Concentrator", "rental_duration_days": 5},
    )
    assert res4.status_code == 422


def test_invalid_required_inputs(client):
    """Test negative duration, zero duration, and invalid date."""
    # Negative duration
    res1 = client.post(
        "/api/allocation/recommend",
        json={
            "equipment": "Oxygen Concentrator",
            "rental_duration_days": -5,
            "request_start": "2026-07-31",
        },
    )
    assert res1.status_code == 422

    # Zero duration
    res2 = client.post(
        "/api/allocation/recommend",
        json={
            "equipment": "Oxygen Concentrator",
            "rental_duration_days": 0,
            "request_start": "2026-07-31",
        },
    )
    assert res2.status_code == 422

    # Invalid date string
    res3 = client.post(
        "/api/allocation/recommend",
        json={
            "equipment": "Oxygen Concentrator",
            "rental_duration_days": 5,
            "request_start": "invalid-date-format",
        },
    )
    assert res3.status_code == 400
    assert "Invalid request_start date" in res3.json()["detail"]


def test_unknown_equipment(client):
    """Test request for non-existent equipment returns 404 with available items."""
    payload = {
        "equipment": "NonExistentLaserDevice",
        "rental_duration_days": 7,
        "request_start": "2026-07-31",
    }
    response = client.post("/api/allocation/recommend", json=payload)
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "NonExistentLaserDevice" in detail
    assert "Available equipment:" in detail


def test_no_suitable_unit_and_next_available_options(client):
    """Test scenario where strict maintenance filters all units and returns next available options."""
    payload = {
        "equipment": "Walker",
        "rental_duration_days": 7,
        "request_start": "2026-07-31",
        "strict_maintenance": True,
    }
    response = client.post("/api/allocation/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["recommendation_status"] == "No suitable unit currently available"
    assert data["recommended_equipment_id"] is None
    assert data["suitability_score"] is None
    assert data["condition"] is None
    assert data["maintenance_status"] is None
    assert len(data["candidates"]) == 0
    assert len(data["next_available_options"]) > 0

    # Verify structure of next available options
    for opt in data["next_available_options"]:
        assert opt["equipment"] == "Walker"
        assert opt["equipment_id"].startswith("WK-")
        assert opt["expected_available_date"] is not None


def test_hard_constraints_enforcement(client):
    """Verify that only units strictly satisfying all 4 hard constraints are present in candidates."""
    # Wheelchair has 20 units total, 18 currently active on 2026-07-31, leaving 2 available
    payload = {
        "equipment": "Wheelchair",
        "rental_duration_days": 5,
        "request_start": "2026-07-31",
    }
    response = client.post("/api/allocation/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["recommendation_status"] == "Recommended"
    assert len(data["candidates"]) == 2

    for c in data["candidates"]:
        assert c["equipment"] == "Wheelchair"
        assert c["availability_score"] == 100.0
        assert 0.0 <= c["suitability_score"] <= 100.0


def test_ranking_and_suitability_score_validity(client):
    """Verify strict monotonic rank order and valid component scores across candidates."""
    payload = {
        "equipment": "Oxygen Concentrator",
        "rental_duration_days": 12,
        "request_start": "2026-07-31",
    }
    response = client.post("/api/allocation/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    candidates = data["candidates"]
    assert len(candidates) > 0

    ranks = [c["rank"] for c in candidates]
    assert ranks == list(range(1, len(candidates) + 1))

    scores = [c["suitability_score"] for c in candidates]
    # Suitability scores must be non-increasing
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1]

    for c in candidates:
        assert 0.0 <= c["suitability_score"] <= 100.0
        assert 0.0 <= c["condition_score"] <= 100.0
        assert 0.0 <= c["maintenance_score"] <= 100.0
        assert 0.0 <= c["availability_window_score"] <= 100.0
        assert 0.0 <= c["duration_fit_score"] <= 100.0
        assert 0.0 <= c["current_utilisation_score"] <= 100.0
        assert 0.0 <= c["future_demand_score"] <= 100.0


def test_exclude_rental_id_simulation(client):
    """Test excluding a rental ID to simulate the moment prior to an existing booking."""
    payload = {
        "equipment": "Oxygen Concentrator",
        "rental_duration_days": 12,
        "request_start": "2026-07-31",
        "exclude_rental_id": "RENT-99999",
    }
    response = client.post("/api/allocation/recommend", json=payload)
    assert response.status_code == 200
    assert response.json()["recommendation_status"] == "Recommended"
