import requests
import json
import sys

def test_predict():
    try:
        with open('artifacts/scenarios/validated/DDoS.json', 'r') as f:
            data = json.load(f)
        
        url = 'http://127.0.0.1:8000/predict'
        payload = {'features': data['features']}
        
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        print(f"STATUS: SUCCESS")
        print(f"PREDICTION: {result.get('attack_type')}")
        print(f"ACTION: {result.get('action')}")
        
    except Exception as e:
        print(f"STATUS: FAILURE")
        print(f"ERROR: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    test_predict()
