import pandas as pd

# Path to your CSV
csv_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Projects\data-steward\gid_requests\GIS_Requests_2026_03_24.csv"

# Load the data
df = pd.read_csv(csv_path)

# Clean column names (avoid hidden spaces issues)
df.columns = df.columns.str.strip()

print("CSV loaded successfully.")
print(f"Total rows: {len(df)}")

# Filter rows where Title contains 'fence' (case-insensitive)
mask = df["Title"].str.contains("fence", case=False, na=False)
filtered_df = df[mask]

print(f"Rows containing 'fence': {len(filtered_df)}\n")

# Group by "Created By"
grouped = (
    filtered_df
    .dropna(subset=["Created By"])
    .groupby("Created By")
    .agg({
        "Title": "count",
        "District Code": lambda x: sorted(set(str(v) for v in x if pd.notna(v)))
    })
    .rename(columns={"Title": "Fence_Count"})
    .sort_values(by="Fence_Count", ascending=False)
)

print("Created By  →  Fence Count  →  District Code(s)\n")

for name, row in grouped.iterrows():
    districts = ", ".join(row["District Code"])
    print(f"{name}  →  {row['Fence_Count']}  →  {districts}")