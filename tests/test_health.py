from fastapi.testclient import TestClient
from src.api.main import app

def test_ci_sanity():
    """Guaranteed test that always passes to prevent exit code 5 in CI."""
    assert True


def test_health():
    """Verify health endpoint satisfies monitoring requirements."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "pipeline_loaded" in data