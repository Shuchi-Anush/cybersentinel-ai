"""
Validates extracted median records against the live inference API.
Iterates over candidates until a confident match against the expected class is found.
Emits the single, validated JSON payload mapping into the finalized artifacts tree.
"""

import os
import json
import time
import logging
import requests

from src.core.paths import ARTIFACTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validator")

SCENARIOS_DIR_CAND = ARTIFACTS_DIR / "scenarios" / "candidates"
SCENARIOS_DIR_VAL = ARTIFACTS_DIR / "scenarios" / "validated"
SCENARIOS_DIR_VAL.mkdir(parents=True, exist_ok=True)
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

def load_candidates():
    candidates = {}
    for filepath in SCENARIOS_DIR_CAND.glob("*_cand_*.json"):
        with open(filepath, "r") as f:
            data = json.load(f)
            label = data["expected"]["attack_type"]
            dist = float(data.get("distance", 999999.0))
            idx = int(data.get("source_index", -1))
            if label not in candidates:
                candidates[label] = []
            candidates[label].append(((dist, idx), filepath, data))
            
    for label in candidates:
        candidates[label].sort(key=lambda x: x[0])  # Sort by (distance, source_index)
    return candidates

def validate_scenarios(candidates):
    final_scenarios = []
    session = requests.Session()
    
    # Try server health first
    try:
        health = session.get(f"{API_URL}/health", timeout=3)
        if health.status_code != 200:
            logger.error("API is not returning HTTP 200 OK.")
            return []
    except Exception as e:
        logger.error(f"Cannot reach API at {API_URL}. Start server: python -m uvicorn src.api.main:app")
        return []

    for label, items in candidates.items():
        logger.info(f"Validating candidates for: {label}")
        match_found = False
        
        for idx, filepath, data in items:
            payload = {"features": data["features"]}
            try:
                resp = None
                for attempt in range(3):
                    try:
                        resp = session.post(f"{API_URL}/predict", json=payload, timeout=5)
                        break
                    except requests.exceptions.RequestException as e:
                        if attempt == 2:
                            raise e
                        time.sleep(1)
                        
                if resp and resp.status_code == 200:
                    result = resp.json()
                    
                    if not result or "action" not in result:
                        logger.warning(f"  [MISSING] Response for {filepath.name} incomplete")
                        continue

                    action = result.get("action")
                    attack_type = result.get("attack_type")
                    
                    # --- Core Validation Logic ---
                    if label == "BENIGN":
                        is_valid = (action == "ALLOW")
                    else:
                        is_valid = (
                            attack_type is not None
                            and attack_type.lower() == label.lower()
                            and action in ["QUARANTINE", "DENY"]
                        )
                        
                    if is_valid:
                        logger.info(f"✅ Class {label} MATCHED on candidate (idx={data['source_index']})")
                        
                        data["label"] = label
                        data["validated"] = True
                        data["model_output"] = {
                            "attack_type": result.get("attack_type"),
                            "action": result.get("action"),
                            "confidence": result.get("confidence")
                        }
                        
                        final_scenarios.append((label, data))
                        match_found = True
                        break
                    else:
                        logger.warning(f"❌ Mismatch for {label}. (Predicted: {result.get('attack_type')}, Action: {result.get('action')})")
                else:
                    logger.error(f"HTTP {resp.status_code} on prediction.")
            except Exception as e:
                logger.error(f"Prediction request failed: {e}")
                
        if not match_found:
            logger.error(f"Failed to find ANY matching representation for {label} across {len(items)} candidates!")

    return final_scenarios

def main():
    candidates = load_candidates()
    if not candidates:
        logger.error("No candidates found! Run scenario_extractor.py first.")
        return
        
    finalized = validate_scenarios(candidates)
    
    # Write finalized outputs (Candidates are automatically preserved)
    for label, data in finalized:
        safe_label = label.replace(" ", "_").replace(".", "")
        target_path = SCENARIOS_DIR_VAL / f"{safe_label}.json"
        with open(target_path, "w") as f:
            json.dump(data, f, indent=2)
            
    logger.info(f"Successfully minted {len(finalized)} dynamic scenarios via deterministic API convergence.")

if __name__ == "__main__":
    main()
