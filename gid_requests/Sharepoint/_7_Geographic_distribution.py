import pandas as pd

# --- INPUTS ---
csv_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_16.csv"

output_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Team_Members\_7_Geographic_distribution.csv"

# --- LOAD CSV ---
df = pd.read_csv(csv_path)

# --- FILTER ---
df = df[
    (df["Request Status"] == "Completed") &
    (df["GIS Staff Assigned"].notna()) &
    (df["District Code"].notna())
].copy()

# --- CLEAN (optional but useful) ---
df["District Code"] = df["District Code"].astype(str).str.strip()

# Ensure unique tasks per staff
df_unique = df.drop_duplicates(subset=["GIS Staff Assigned", "ID"]).copy()

# --- GROUP & COUNT ---
grouped = (
    df_unique.groupby(["GIS Staff Assigned", "District Code"])
    .agg(Task_Count=("ID", "nunique"))
    .reset_index()
)

# --- CALCULATE TOTAL PER STAFF ---
grouped["Total per Staff"] = grouped.groupby("GIS Staff Assigned")["Task_Count"].transform("sum")

# --- CALCULATE % ---
grouped["Percent (%)"] = (
    grouped["Task_Count"] / grouped["Total per Staff"] * 100
).round(2)

# --- SORT ---
grouped = grouped.sort_values(
    by=["GIS Staff Assigned", "Task_Count"],
    ascending=[True, False]
)

# --- SAVE ---
grouped.to_csv(output_path, index=False)

print(f"Output saved to:\n{output_path}")