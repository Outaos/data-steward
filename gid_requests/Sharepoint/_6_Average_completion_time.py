import pandas as pd

# --- INPUTS ---
csv_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_16.csv"

output_folder = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Team_Members"

output_total = output_folder + r"\_6_Average_completion_time_total.csv"
output_category = output_folder + r"\_6_Average_completion_time_by_category.csv"

# --- LOAD CSV ---
df = pd.read_csv(csv_path)

# --- FILTER ---
df = df[
    (df["Request Status"] == "Completed") &
    (df["GIS Staff Assigned"].notna()) &
    (df["GIS Start Date"].notna()) &
    (df["GIS Completion Date"].notna())
].copy()

# --- DATE FIELDS ---
df["GIS Start Date"] = pd.to_datetime(df["GIS Start Date"], errors="coerce")
df["GIS Completion Date"] = pd.to_datetime(df["GIS Completion Date"], errors="coerce")

df = df[
    df["GIS Start Date"].notna() &
    df["GIS Completion Date"].notna()
].copy()

# --- CALCULATE COMPLETION TIME ---
df["Completion Days"] = (df["GIS Completion Date"] - df["GIS Start Date"]).dt.days

# Remove bad values if any
df = df[df["Completion Days"] >= 0].copy()

# Ensure unique tasks per staff
df_unique = df.drop_duplicates(subset=["GIS Staff Assigned", "ID"]).copy()

# --- TOTAL PER STAFF ---
total_avg = (
    df_unique.groupby("GIS Staff Assigned")
    .agg(
        Total_Completed_Tasks=("ID", "nunique"),
        Average_Completion_Days=("Completion Days", "mean")
    )
    .reset_index()
)

total_avg["Average_Completion_Days"] = total_avg["Average_Completion_Days"].round(2)
total_avg = total_avg.sort_values(by="Average_Completion_Days", ascending=False)

# --- BY CATEGORY ---
by_category = (
    df_unique.groupby(["GIS Staff Assigned", "Request Category"])
    .agg(
        Completed_Tasks=("ID", "nunique"),
        Average_Completion_Days=("Completion Days", "mean")
    )
    .reset_index()
)

by_category["Average_Completion_Days"] = by_category["Average_Completion_Days"].round(2)
by_category = by_category.sort_values(
    by=["GIS Staff Assigned", "Average_Completion_Days"],
    ascending=[True, False]
)

# --- SAVE CSVs ---
total_avg.to_csv(output_total, index=False)
by_category.to_csv(output_category, index=False)

print(f"Outputs saved to:\n{output_total}\n{output_category}")