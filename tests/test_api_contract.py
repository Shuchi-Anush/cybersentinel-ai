"""
API contract tests — CI safe.

These tests verify correctness of non-inference endpoints and
schema structure without requiring models to be loaded.
"""
import os
import pytest
from fastapi.testclient import TestClient
from src.api.main import app


def test_empty_features_rejected():
    """INVALID INPUT — empty features dict must be rejected with 422."""
    with TestClient(app) as client:
        response = client.post("/predict", json={"features": {}})
        assert response.status_code == 422


def test_pipeline_failure_simulation():
    """
    Simulate a pipeline loading error and ensure:
    1. /health reflects the error
    2. /predict returns 500
    3. /meta/eval still returns 200
    """
    with TestClient(app) as client:
        # Force error state
        app.state.pipeline = None
        app.state.pipeline_ready = False
        app.state.pipeline_error = "Simulated disk failure"

        # 1. Health
        h_res = client.get("/health")
        h_data = h_res.json()
        assert h_data["status"] == "starting"
        assert h_data["pipeline_error"] == "Simulated disk failure"

        # 2. Predict must 500 when pipeline_error is set
        p_res = client.post("/predict", json={"features": {"test": 1}})
        assert p_res.status_code == 500
        assert "Simulated disk failure" in p_res.json()["detail"]

        # 3. Meta eval must still respond 200
        m_res = client.get("/meta/eval")
        assert m_res.status_code == 200
        assert m_res.json().get("status") in ("ok", "missing")

        # Reset state
        app.state.pipeline_error = None


def test_predict_response_contains_trust():
    """
    When pipeline IS loaded, /predict must include the full Zero-Trust schema.
    Skipped in CI where models are absent.
    """
    if os.getenv("CI") == "true":
        pytest.skip("Model-dependent test skipped in CI")

    with TestClient(app) as client:
        # Wait for pipeline — TestClient runs lifespan synchronously
        health = client.get("/health").json()
        if not health.get("pipeline_ready"):
            pytest.skip("Pipeline not ready")

        # Load feature list
        import joblib
        from pathlib import Path
        features = joblib.load(Path("models/binary/features.pkl"))
        payload = {"features": {f: 0.0 for f in features}}

        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()

        # Full schema check
        assert "action" in data
        assert "confidence" in data
        assert "prediction" in data
        assert "trust" in data
        assert "trust_score" in data["trust"]
        assert "risk_level" in data["trust"]
        assert data["trust"]["risk_level"] in ("LOW", "MEDIUM", "HIGH")


def test_ci_sanity():
    """Ensures pytest never exits with 0 tests collected."""
    assert True
