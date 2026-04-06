import requests
import json
import time

API_URL = "http://127.0.0.1:8000"

def test_endpoint(name, method, path, data=None):
    print(f"--- Running Stress Test: {name} ---")
    try:
        if method == "GET":
            response = requests.get(f"{API_URL}{path}")
        else:
            response = requests.post(f"{API_URL}{path}", json=data)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code
    except Exception as e:
        print(f"Error: {e}")
        return 500

def run_stress_tests():
    # 1. Health check
    test_endpoint("Health Check", "GET", "/health")

    # 2. Valid Input (from existing sample if possible, or dummy)
    # Note: Requires training to be finished for real validation
    dummy_features = {f"feat_{i}": 0.0 for i in range(78)} # adjust for real feature count
    test_endpoint("Valid Payload (Dummy Features)", "POST", "/predict", {"features": dummy_features})

    # 3. Missing Features Key
    test_endpoint("Missing 'features' key", "POST", "/predict", {"junk": {}})

    # 4. Empty JSON
    test_endpoint("Empty JSON", "POST", "/predict", {})

    # 5. Extra Fields
    test_endpoint("Extra Fields", "POST", "/predict", {"features": dummy_features, "malicious_payload": "DROP TABLE users;"})

    # 6. Invalid Data Types
    test_endpoint("Invalid Data Types", "POST", "/predict", {"features": {"Destination Port": "STRING_NOT_PORT"}})

if __name__ == "__main__":
    run_stress_tests()
