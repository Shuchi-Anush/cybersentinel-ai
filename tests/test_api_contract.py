import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_predict_contract():
    """
    REQUIRED API CONTRACT (MANDATORY)
    ALL "/predict" responses MUST be EXACTLY:
    {
      "action": string,
      "confidence": float,
      "attack_type": string | null
    }
    """
    # Wait for app to be ready if needed, but TestClient handles lifespan
    payload = {"features": {"Flow Duration": 1.0, "Total Fwd Packets": 2.0}}
    response = client.post("/predict", json=payload)
    
    # If model is loading, it might return 503, but in test it should be fast
    if response.status_code == 503:
        pytest.skip("Model still loading in test environment")
        
    assert response.status_code == 200
    data = response.json()

    # Strict key check
    assert set(data.keys()) == {"action", "confidence", "attack_type"}
    
    # Type validation
    assert isinstance(data["action"], str)
    assert isinstance(data["confidence"], float)
    assert data["attack_type"] is None or isinstance(data["attack_type"], str)

def test_empty_features():
    """INVALID INPUT TEST - Empty features should be rejected with 422."""
    payload = {"features": {}}
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

def test_meta_eval_contract():
    """
    /meta/eval MUST ALWAYS return HTTP 200.
    Schema matches exactly.
    """
    response = client.get("/meta/eval")
    # Rule: Meta endpoints NEVER 503
    assert response.status_code == 200 
    data = response.json()
    assert "f1_macro" in data
    assert "status" in data
    assert isinstance(data["f1_macro"], float)
    assert data["status"] in ["ok", "missing"]

def test_pipeline_failure_simulation():
    """
    Simulate a pipeline loading error and ensure:
    1. /health shows the error
    2. /predict returns 500
    3. /meta/eval still returns 200
    """
    # Force error state in app state
    app.state.ready = False
    app.state.pipeline = None
    app.state.pipeline_error = "Simulated disk failure"
    
    # 1. Health
    h_res = client.get("/health")
    h_data = h_res.json()
    assert h_data["status"] == "starting" # Logic: 'ok' only if ready
    assert h_data["pipeline_error"] == "Simulated disk failure"
    
    # 2. Predict
    p_res = client.post("/predict", json={"features": {"test": 1}})
    assert p_res.status_code == 500
    assert "Simulated disk failure" in p_res.json()["detail"]
    
    # 3. Meta
    m_res = client.get("/meta/eval")
    assert m_res.status_code == 200
    assert m_res.json()["status"] == "missing"
