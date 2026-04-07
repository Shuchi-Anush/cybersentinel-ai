import pytest
from fastapi.testclient import TestClient
from src.api.main import app

def test_ci_sanity():
    """Guaranteed test that always passes to prevent exit code 5 in CI."""
    assert True

def test_health():
    """
    /health must always return 200 with status='ok'.
    pipeline_ready reflects whether pipeline has been lazily loaded.
    STRICT RULE: Does NOT trigger load().
    """
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert "pipeline_ready" in data
        
        # In a fresh TestClient session, pipeline should NOT be ready yet
        assert data["pipeline_ready"] is False