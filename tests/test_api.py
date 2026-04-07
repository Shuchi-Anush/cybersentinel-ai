import os
import pytest
import joblib
from pathlib import Path
from fastapi.testclient import TestClient
from src.api.main import app

def get_required_features():
    """Load the official feature list once for test generation."""
    f_path = Path("models/binary/features.pkl")
    if not f_path.exists():
        return []
    return joblib.load(f_path)


def test_health_in_api():
    """Verify health endpoint satisfies monitoring requirements."""
    # NO TestClient at module level
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "pipeline_ready" in data


def test_predict_single():
    """Verify single flow prediction with dynamically discovered features."""
    if os.getenv("CI") == "true":
        pytest.skip("Skipping model-dependent tests in CI")

    features = get_required_features()
    if not features:
        pytest.skip("features.pkl not found")

    payload = {
        "features": {f: 0.1 for f in features}
    }
    
    with TestClient(app) as client:
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "action" in data
        assert "confidence" in data
        assert "attack_type" in data


def test_predict_batch():
    """Verify batch flow prediction with dynamically discovered features."""
    if os.getenv("CI") == "true":
        pytest.skip("Skipping model-dependent tests in CI")

    features = get_required_features()
    if not features:
        pytest.skip("features.pkl not found")

    payload = {
        "flows": [
            {f: 0.1 for f in features},
            {f: 0.2 for f in features}
        ]
    }
    
    with TestClient(app) as client:
        response = client.post("/predict/batch", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2


def test_predict_invalid_nan():
    """Verify that Inf/NaN values are rejected."""
    if os.getenv("CI") == "true":
        pytest.skip("Skipping model-dependent tests in CI")

    features = get_required_features()
    if not features:
        pytest.skip("features.pkl not found")

    # Manually construct JSON with Infinity to test API's robust check
    raw_json = '{"features": {"' + features[0] + '": Infinity}}'
    
    with TestClient(app) as client:
        response = client.post(
            "/predict", 
            content=raw_json, 
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


def test_predict_failure_in_ci():
    """Verify that /predict returns 503 in CI (where models are missing)."""
    if os.getenv("CI") != "true":
        pytest.skip("Only run in CI environment")

    with TestClient(app) as client:
        response = client.post("/predict", json={"features": {"f1": 0.0}})
        # Even with invalid schema, lazy-load should trigger first and fail with 503
        assert response.status_code == 503
        assert "Model loading disabled in CI" in response.json()["error"]


def test_ci_sanity_in_api():
    """Ensures pytest never exits with 0 tests collected."""
    assert True
