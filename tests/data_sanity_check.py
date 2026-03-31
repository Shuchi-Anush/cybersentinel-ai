import pandas as pd

df = pd.read_csv("data/processed/merged_cleaned.csv")
print(df.head())
print(df["Flow Duration"].describe())