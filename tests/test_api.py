import pytest
from pathlib import Path

# 🔥 MUST be before importing app
if not Path("models/binary/features.pkl").exists():
    pytest.skip(
        "Skipping API tests: models not available in CI",
        allow_module_level=True
    )

from fastapi.testclient import TestClient
from src.api.main import app

import joblib
from fastapi.testclient import TestClient
from src.api.main import app

def get_required_features():
    """Load the official feature list once for test generation."""
    f_path = Path("models/binary/features.pkl")
    if not f_path.exists():
        return []
    return joblib.load(f_path)

def test_health():
    """Verify health endpoint satisfies monitoring requirements."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "pipeline_loaded" in response.json()

def test_predict_single():
    """Verify single flow prediction with dynamically discovered features."""
    features = get_required_features()
    if not features:
        pytest.skip("Models/features.pkl not found. Skipping inference test.")
        
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
    features = get_required_features()
    if not features:
        pytest.skip("Models/features.pkl not found. Skipping inference test.")
        
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
    """Verify that Inf/NaN values are rejected.
    Uses raw string to bypass standard JSON serialization limits for infinity.
    """
    features = get_required_features()
    if not features:
        pytest.skip("Models/features.pkl not found.")
        
    # Manually construct JSON with Infinity to test API's robust check
    raw_json = '{"features": {"' + features[0] + '": Infinity}}'
    
    with TestClient(app) as client:
        response = client.post(
            "/predict", 
            content=raw_json, 
            headers={"Content-Type": "application/json"}
        )
        # Pydantic or our custom check should catch this
        assert response.status_code == 422
