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


def test_health_always_ok():
    """
    /health must always return 200 and never trigger pipeline loading.
    pipeline_ready is False before any /predict call — that is correct and expected.
    """
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "pipeline_ready" in data

        # pipeline_error should be None (no error has occurred)
        assert data.get("pipeline_error") is None


def test_meta_eval_always_responds():
    """/meta/eval must respond 200 regardless of pipeline state."""
    with TestClient(app) as client:
        response = client.get("/meta/eval")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ("ok", "missing")


def test_predict_response_contains_trust():
    """
    When pipeline IS loaded, /predict must include the full Zero-Trust schema.
    Skipped in CI where models are absent.
    """
    if os.getenv("CI") == "true":
        pytest.skip("Model-dependent test skipped in CI")

    import joblib
    from pathlib import Path

    features_path = Path("models/binary/features.pkl")
    if not features_path.exists():
        pytest.skip("features.pkl not found — models not available")

    features = joblib.load(features_path)
    payload = {"features": {f: 0.0 for f in features}}

    with TestClient(app) as client:
        response = client.post("/predict", json=payload)
        assert response.status_code == 200
        data = response.json()

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
