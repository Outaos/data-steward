import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

print("🚀 Script started")

file_path = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_10.csv")

if not file_path.exists():
    print("❌ File does NOT exist!")
    exit()

df = pd.read_csv(file_path)
print(f"✅ CSV loaded. Rows: {len(df)}")

title_col = "Title"
date_col = "Request Submission Date" #"GIS Completion Date"

required_cols = [title_col, date_col]
missing = [col for col in required_cols if col not in df.columns]

if missing:
    print(f"❌ Missing columns: {missing}")
    exit()

df[title_col] = df[title_col].fillna("").astype(str)
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

matched_df = df.copy()

print(f"✅ Matches found: {len(matched_df)}")

start_date = pd.Timestamp("2025-04-01")
end_date = pd.Timestamp.today()

# Split into completed (in range) and pending (no date)
completed_df = matched_df[
    matched_df[date_col].notna() &
    (matched_df[date_col] >= start_date) &
    (matched_df[date_col] <= end_date)
].copy()

#pending_count = matched_df[matched_df[date_col].isna()].shape[0]
#pending_count = matched_df[matched_df["GIS Completion Date"].isna()].shape[0]

# Monthly aggregation
completed_df["month"] = completed_df[date_col].dt.to_period("M").dt.to_timestamp()
all_months = pd.date_range(start_date, end_date, freq="MS")   # ("2025-06-01", "2026-03-01", freq="MS")

monthly_summary = (
    completed_df
    .groupby("month")
    .size()
    .reindex(all_months, fill_value=0)
    .reset_index()
)

monthly_summary.columns = ["month", "gis_requests"]
monthly_summary["month_label"] = monthly_summary["month"].dt.strftime("%b %Y")

# Add Pending Requests row
#pending_row = pd.DataFrame({
#    "month": [pd.NaT],
# "gis_requests": [pending_count],
#    "month_label": ["Pending Requests"]
#})

monthly_summary = pd.concat([monthly_summary], ignore_index=True)  #, pending_row

print("\n📊 Monthly Summary (with Pending Requests):")
print(monthly_summary[["month_label", "gis_requests"]].to_string(index=False))

# =========================
# OUTPUT
# =========================
import numpy as np
from matplotlib import cm
from matplotlib.colors import Normalize

sns.set(style="whitegrid")

output_folder = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Charts")
output_folder.mkdir(parents=True, exist_ok=True)

plt.figure(figsize=(12, 6))

values = monthly_summary["gis_requests"]

norm = Normalize(vmin=values.min(), vmax=values.max())
cmap = cm.get_cmap("Blues")

min_intensity = 0.35
max_intensity = 0.85

colors = [
    cmap(min_intensity + (max_intensity - min_intensity) * norm(v))
    for v in values
]

ax = sns.barplot(
    data=monthly_summary,
    x="month_label",
    y="gis_requests",
    palette=colors
)
ax.set_yticks([])
ax.set_ylabel("")
sns.despine(left=True)
# Add value labels
#for i, v in enumerate(values):
#    ax.text(i, v + 0.2, str(int(v)), ha="center", va="bottom")

# Grid styling
ax.yaxis.grid(True, linestyle='-', linewidth=1, alpha=0.3)
ax.xaxis.grid(False)

plt.title("GIS Requests by Month")
plt.xlabel("Month")
plt.ylabel("Number of Requests")
plt.xticks(rotation=45)
plt.tight_layout()

chart_path = output_folder / "gis_requests_by_month.png"
plt.savefig(chart_path, dpi=300)
plt.close()

print(f"📊 Saved: {chart_path}")
print("🎉 Done")