import pandas as pd

# --- INPUTS ---
csv_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_16.csv"

output_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Team_Members\_3_Request_urgency_distribution.csv"

# --- LOAD CSV ---
df = pd.read_csv(csv_path)

# --- FILTER ---
df = df[
    (df["Request Status"] == "Completed") &
    (df["GIS Staff Assigned"].notna()) &
    (df["Request Time Frame"].notna())
]

# --- NORMALIZE URGENCY ---
def map_urgency(val):
    val = str(val).strip()

    if val in ["1 - High", "1 - Urgent"]:
        return "1 - High/Urgent"
    elif val in ["2 - Medium", "2 - Expedited"]:
        return "2 - Medium/Expedited"
    elif val in ["3 - Standard", "3 - Low"]:
        return "3 - Standard/Low"
    else:
        return "Other"

df["Urgency Group"] = df["Request Time Frame"].apply(map_urgency)

# Optional: remove "Other" if you don’t want noise
df = df[df["Urgency Group"] != "Other"]

# --- GROUP & COUNT ---
grouped = (
    df.groupby(["GIS Staff Assigned", "Urgency Group"])
    .size()
    .reset_index(name="Task Count")
)

# --- CALCULATE % ---
grouped["Total per Staff"] = grouped.groupby("GIS Staff Assigned")["Task Count"].transform("sum")

grouped["Percent (%)"] = (
    grouped["Task Count"] / grouped["Total per Staff"] * 100
).round(2)

# --- SORT ---
grouped = grouped.sort_values(
    by=["GIS Staff Assigned", "Urgency Group"]
)

# --- SAVE ---
grouped.to_csv(output_path, index=False)

print(f"Output saved to:\n{output_path}")