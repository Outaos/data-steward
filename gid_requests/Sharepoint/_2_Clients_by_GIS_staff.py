import pandas as pd

# --- INPUTS ---
csv_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_16.csv"

output_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Team_Members\_2_Clients_by_GIS_staff.csv"

# --- LOAD CSV ---
df = pd.read_csv(csv_path)

# Optional: clean
df = df.dropna(subset=["GIS Staff Assigned", "Created By"])

# --- GROUP & COUNT ---
grouped = (
    df.groupby(["GIS Staff Assigned", "Created By"])
    .size()
    .reset_index(name="Task Count")
)

# --- CALCULATE % WITHIN EACH GIS STAFF ---
grouped["Total Tasks per Staff"] = grouped.groupby("GIS Staff Assigned")["Task Count"].transform("sum")

grouped["Percent (%)"] = (
    grouped["Task Count"] / grouped["Total Tasks per Staff"] * 100
).round(2)

# --- SORT (most common clients first per staff) ---
grouped = grouped.sort_values(
    by=["GIS Staff Assigned", "Task Count"],
    ascending=[True, False]
)

# --- SAVE OUTPUT ---
grouped.to_csv(output_path, index=False)

print(f"Output saved to:\n{output_path}")