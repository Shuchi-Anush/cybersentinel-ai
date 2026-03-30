# scripts/generate_payload_quarantine.py

import pandas as pd, json

df = pd.read_csv("data/raw/attack_raw_sample.csv")

df = df[df["Label"].isin([
    "PortScan",
    "FTP-Patator",
    "SSH-Patator"
])]

with open("configs/selected_features.json") as f:
    selected = json.load(f)["selected_features"]

row = df.sample(1).iloc[0]

payload = {"features": {f: float(row[f]) for f in selected}}

print(json.dumps(payload, indent=2))