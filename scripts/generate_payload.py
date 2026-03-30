import pandas as pd
import json
import argparse
import sys
from pathlib import Path
import random

# -----------------------------
# CONFIG
# -----------------------------
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "attack_raw_sample.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "selected_features.json"

def get_fallback_payload(selected_features):
    """Generate a synthetic payload if data is missing."""
    return {
        "features": {f: round(random.uniform(0, 100), 4) for f in selected_features}
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["benign", "quarantine", "attack"], required=True)
    args = parser.parse_args()

    # 1. Load Features
    try:
        with open(CONFIG_PATH) as f:
            selected = json.load(f)["selected_features"]
    except Exception:
        # Extreme fallback if config is also missing
        selected = ["Destination Port", "Flow Duration", "Total Fwd Packets"]

    # 2. Try to Load Real Data
    payload = None
    if DATA_PATH.exists():
        try:
            df = pd.read_csv(DATA_PATH)
            
            # Filter logic
            if args.type == "benign":
                subset = df[df["Label"] == "BENIGN"]
            elif args.type == "attack":
                subset = df[df["Label"] == "DoS slowloris"]
            elif args.type == "quarantine":
                subset = df[df["Label"].isin(["PortScan", "FTP-Patator", "SSH-Patator"])]
            else:
                subset = pd.DataFrame()

            if not subset.empty:
                row = subset.sample(1).iloc[0]
                payload = {
                    "features": {f: float(row[f]) for f in selected}
                }
        except Exception:
            pass # Fallback to synthetic

    # 3. Final Fallback
    if payload is None:
        payload = get_fallback_payload(selected)

    # 4. Output
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()