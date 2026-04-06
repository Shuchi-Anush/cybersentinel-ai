# scripts/generate_payload_benign.py

import pandas as pd, json
import sys
from pathlib import Path

from src.core.paths import PROCESSED_DATA_DIR, CONFIGS_DIR

df = pd.read_csv(PROCESSED_DATA_DIR / "merged_cleaned.csv")
df = df[df["Label"] == "BENIGN"]

with open(CONFIGS_DIR / "selected_features.json") as f:
    selected = json.load(f)["selected_features"]

row = df.sample(1).iloc[0]

payload = {"features": {f: float(row[f]) for f in selected}}

print(json.dumps(payload, indent=2))