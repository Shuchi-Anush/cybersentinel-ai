import requests
import json
import subprocess
import sys
import os
from pathlib import Path

# Ensure project root
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

BASE_URL = "http://localhost:8000/predict"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "generate_payload.py"

def generate_payload(payload_type):
    """Generate a payload by calling the generator script."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--type", payload_type],
            capture_output=True,
            text=True,
            check=True
        )
        if not result.stdout.strip():
            raise RuntimeError("Empty payload output")

        print("RAW PAYLOAD OUTPUT:\n", result.stdout)

        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating payload: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print("❌ Error decoding payload JSON.")
        return None

def hit_api(payload):
    """Send payload to the CyberSentinel API."""
    try:
        response = requests.post(BASE_URL, json=payload, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API Request Failed: {e}")
        return None

def run_case(case):
    """Run a single test case (benign, quarantine, or attack)."""
    print(f"\n🚀 CASE: {case.upper()}")
    print("-" * 30)
    
    payload = generate_payload(case)
    if not payload:
        return

    result = hit_api(payload)
    if not result:
        return

    print(f"Action      : {result.get('action', 'N/A')}")
    print(f"Confidence  : {result.get('confidence', 'N/A')}")
    print(f"Attack Type : {result.get('attack_type', 'N/A')}")
    print(f"Reason      : {result.get('reason', 'N/A')}")

def main():
    print("🛡️ CyberSentinel-AI — Production Demo")
    print("=" * 40)
    
    # Check if API is up
    try:
        health = requests.get("http://localhost:8000/health", timeout=2).json()
        print(f"Status: {health.get('status')} | Pipeline: {health.get('pipeline_loaded')}")
    except:
        print("⚠️ API is unreachable. Please start the server: uvicorn src.api.main:app")
        return

    for case in ["benign", "quarantine", "attack"]:
        run_case(case)

if __name__ == "__main__":
    main()