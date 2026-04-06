"""
Extracts data-driven, validated representative attack scenarios using the raw splits.
Finds Top-K median row candidates based on 40 strict features.
"""

import json
import logging
from datetime import datetime
import pandas as pd
from scipy.spatial.distance import cdist

# Setup paths using the core module
from src.core.paths import PROCESSED_DATA_DIR, CONFIGS_DIR, ARTIFACTS_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extractor")

SCENARIOS_OUT_DIR = ARTIFACTS_DIR / "scenarios" / "candidates"
SCENARIOS_OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CLASSES = [
    "BENIGN",
    "DDoS",
    "DoS slowloris",
    "SSH-Patator",
    "PortScan",
    "Infiltration"
]

def load_policy():
    import yaml
    policy_path = CONFIGS_DIR / "policy.yaml"
    with open(policy_path, "r") as f:
        return yaml.safe_load(f)["policy"]

def get_expected_action(label: str, policy: dict) -> str:
    if label == "BENIGN":
        return "ALLOW"
    if label in policy.get("deny_classes", []):
        return "DENY"
    if label in policy.get("quarantine_classes", []):
        return "QUARANTINE"
    return policy.get("default_attack_action", "QUARANTINE")

def extract_candidates(df: pd.DataFrame, features: list, label: str, top_k: int = 5):
    subset = df[df["Label"] == label].copy()
    if subset.empty:
        logger.warning(f"No samples found for {label}")
        return []

    # Reset index so we can map distances gracefully
    subset = subset.reset_index()
    
    # Calculate median row for numerical features
    X = subset[features].astype(float)
    median_vector = X.median().values.reshape(1, -1)

    # Compute euclidean distances to the median for all rows
    distances = cdist(X.values, median_vector, metric='euclidean').flatten()
    
    # Sort by (distance, index) to ensure determinism
    # Create an array of tuples (distance, original_index, internal_iloc)
    records = []
    for i, dist in enumerate(distances):
        records.append((dist, subset.loc[i, "index"], i))
        
    records.sort(key=lambda x: (x[0], x[1]))
    
    candidates = []
    for i in range(min(top_k, len(records))):
        dist, orig_idx, iloc_idx = records[i]
        row_data = subset.iloc[iloc_idx]
        candidates.append({
            "expected": {
                "attack_type": label,
                "action": "PENDING" # Assigned later
            },
            "validated": False,
            "source_index": int(orig_idx),
            "distance": float(dist),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "features": {f: float(row_data[f]) for f in features}
        })
    return candidates

def main():
    logger.info("Loading policy...")
    policy = load_policy()

    logger.info("Loading configured selected features...")
    with open(CONFIGS_DIR / "selected_features.json", "r") as f:
        features = json.load(f)["selected_features"]

    data_file = PROCESSED_DATA_DIR / "merged_cleaned.csv"
    logger.info(f"Loading generated dataset from {data_file}")
    df = pd.read_csv(data_file)
    df.columns = df.columns.str.strip()
    
    for cls in TARGET_CLASSES:
        logger.info(f"Extracting scenarios for {cls}...")
        candidates = extract_candidates(df, features, cls, top_k=5)
        for i, cand in enumerate(candidates):
            cand["expected"]["action"] = get_expected_action(cls, policy)
            out_path = SCENARIOS_OUT_DIR / f"{cls.replace(' ', '_')}_cand_{i}.json"
            with open(out_path, "w") as f:
                json.dump(cand, f, indent=2)
        logger.info(f"Saved {len(candidates)} candidates for {cls}.")

if __name__ == "__main__":
    main()
