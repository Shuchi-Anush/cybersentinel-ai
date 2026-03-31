import pandas as pd
import json
import argparse
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "merged_cleaned.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "selected_features.json"
META_PATH = PROJECT_ROOT / "models" / "preprocessing_metadata.json"

def get_fallback_payload(selected_features):
    """
    Generate a neutral fallback payload using training means.
    Ensures zero randomness and realistic feature magnitudes.
    """
    try:
        with open(META_PATH, "r") as f:
            meta = json.load(f)
            stats = meta.get("feature_stats", {})
            return {
                "features": {f: float(stats.get(f, 0.0)) for f in selected_features}
            }
    except Exception:
        # Emergency zero-baseline if metadata also missing
        return {
            "features": {f: 0.0 for f in selected_features}
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
        selected = ["Destination Port", "Flow Duration", "Total Fwd Packets"]

    # 2. Try to Load Real Data
    payload = None
    if DATA_PATH.exists():
        try:
            df = pd.read_csv(DATA_PATH)
            
            subset = pd.DataFrame()
            if args.type == "benign":
                subset = df[df["Label"] == "BENIGN"]
            elif args.type == "quarantine":
                # Categories mapped to QUARANTINE policy in policy.yaml
                q_labels = ["PortScan", "Bot", "Infiltration", "Web Attack - Brute Force"]
                subset = df[df["Label"].isin(q_labels)]
            elif args.type == "attack":
                # High-risk categories mapped to DENY policy in policy.yaml
                a_labels = ["DoS slowloris", "DoS Hulk", "DDoS"]
                subset = df[df["Label"].isin(a_labels)]

            # Safety fallback for row selection
            if not subset.empty:
                row = subset.iloc[0]
                payload = {
                    "features": {f: float(row[f]) for f in selected}
                }
            else:
                # If no specific labels found, take first available row as global safety
                row = df.iloc[0]
                payload = {
                    "features": {f: float(row[f]) for f in selected}
                }
        except Exception as e:
            # Re-raise for debugging if strict mode, but here we fallback
            pass

    # 3. Final Fallback (Mean-based, zero random)
    if payload is None:
        payload = get_fallback_payload(selected)

    # 4. Output PURE JSON
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()