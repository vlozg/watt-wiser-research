
import pandas as pd, numpy as np, sys, os
p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'repo', 'WattWiser', 'data', 'raw', 'synthetic_shelly_data.csv')
df = pd.read_csv(p)
print("SHAPE:", df.shape)
print("COLUMNS:", df.columns.tolist())
print("\nDTYPES:\n", df.dtypes.to_string())
print("\nHEAD:\n", df.head(6).to_string())
print("\nTAIL:\n", df.tail(3).to_string())
print("\nMISSING:", df.isnull().sum().sum(), "| DUPLICATE ROWS:", df.duplicated().sum())

df["timestamp"] = pd.to_datetime(df["timestamp"])
print("\nTIMESTAMP: first", df["timestamp"].min(), "last", df["timestamp"].max())
print("SPAN:", df["timestamp"].max() - df["timestamp"].min())
td = df["timestamp"].diff().dropna()
print("INTERVAL value_counts:\n", td.value_counts().head(8).to_string())
print("MONOTONIC:", df["timestamp"].is_monotonic_increasing)

print("\n=== CARDINALITY (unique values per column) ===")
for c in df.columns:
    print(f"  {c:28s} {df[c].nunique():>9,}")

print("\n=== RANGES ===")
print(df.describe().T.to_string())
