import pandas as pd

# --- INPUTS ---
csv_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_16.csv"

output_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Team_Members\_4_Overdue_requests.csv"

# --- LOAD CSV ---
df = pd.read_csv(csv_path)

# --- PREP ---
df["Days To Complete"] = pd.to_numeric(df["Days To Complete"], errors="coerce")
df = df[df["GIS Staff Assigned"].notna()].copy()

# Ensure unique tasks per staff
df_unique = df.drop_duplicates(subset=["GIS Staff Assigned", "ID"]).copy()

# --- FLAGS ---
df_unique["Is Overdue"] = df_unique["Days To Complete"] < 0
df_unique["Is_Minus_1_2"] = df_unique["Days To Complete"].isin([-1, -2])

# --- GROUP ---
grouped = (
    df_unique.groupby("GIS Staff Assigned")
    .agg(
        Total_Unique_Tasks=("ID", "nunique"),
        Overdue_Tasks=("Is Overdue", "sum"),
        Overdue_Minus_1_2=("Is_Minus_1_2", "sum")
    )
    .reset_index()
)

# --- CALCULATE % ---
grouped["Percent Overdue (%)"] = (
    grouped["Overdue_Tasks"] / grouped["Total_Unique_Tasks"] * 100
).round(2)

grouped["Percent of Overdue = -1/-2 (%)"] = (
    grouped["Overdue_Minus_1_2"] / grouped["Overdue_Tasks"] * 100
).round(2)

# Handle division by zero
grouped["Percent of Overdue = -1/-2 (%)"] = grouped["Percent of Overdue = -1/-2 (%)"].fillna(0)

# --- SORT ---
grouped = grouped.sort_values(by="Percent Overdue (%)", ascending=False)

# --- SAVE ---
grouped.to_csv(output_path, index=False)

print(f"Output saved to:\n{output_path}")