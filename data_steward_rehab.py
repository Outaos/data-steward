import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

print("🚀 Script started")

file_path = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Projects\data-steward\gid_requests\GIS_Requests_2026_03_24.csv")

if not file_path.exists():
    print("❌ File does NOT exist!")
    exit()

df = pd.read_csv(file_path)
print(f"✅ CSV loaded. Rows: {len(df)}")

title_col = "Title"
time_col = "Time Spent (hrs)"
district_col = "District Code"
date_col = "GIS Completion Date"

required_cols = [title_col, time_col, district_col, date_col]
missing = [col for col in required_cols if col not in df.columns]

if missing:
    print(f"❌ Missing columns: {missing}")
    exit()

df[title_col] = df[title_col].fillna("").astype(str)
df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0)
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

pattern = r"\b(?:K\d{5}|N\d{5}|C\d{5})\b|rehab"
include_mask = df[title_col].str.contains(pattern, case=False, na=False, regex=True)
exclude_mask = df[title_col].str.contains(r"BARC", case=False, na=False)

matched_df = df[include_mask & ~exclude_mask].copy()

print(f"✅ Matches found (excluding BARC): {len(matched_df)}")

district_summary = (
    matched_df
    .groupby(district_col, dropna=False)
    .agg(
        matching_rows=(title_col, "size"),
        total_time_spent_hrs=(time_col, "sum")
    )
    .reset_index()
)

print("\n📊 Summary by District Code:")
print(district_summary.to_string(index=False))

# =========================
# OUTPUT PATH
# =========================
sns.set(style="whitegrid")

output_folder = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\SHAREPOINT_STATS\Rehab_stats\Outputs")
output_folder.mkdir(parents=True, exist_ok=True)

# Sort descending (top = highest)
district_summary_sorted_rows = district_summary.sort_values("matching_rows", ascending=False)
district_summary_sorted_time = district_summary.sort_values("total_time_spent_hrs", ascending=False)

# =========================
# CHART 1: GIS Requests by District
# =========================
plt.figure(figsize=(10, 6))

ax = sns.barplot(
    data=district_summary_sorted_rows,
    x="matching_rows",
    y=district_col
)

# Add value labels at end of bars
for i, v in enumerate(district_summary_sorted_rows["matching_rows"]):
    ax.text(v + 0.1, i, f"{int(v)}", va='center')

# Add horizontal lines across bars
ax.yaxis.grid(True, linestyle='-', linewidth=1, alpha=0.3)
ax.xaxis.grid(False)

plt.title("GIS Requests by District")
plt.xlabel("Number of Requests")
plt.ylabel("District Code")

plt.tight_layout()

chart1_path = output_folder / "gis_requests_by_district.png"
plt.savefig(chart1_path)
plt.close()

print(f"📊 Saved: {chart1_path}")

# =========================
# CHART 2: Total Time Spent by District (Hours)
# =========================
plt.figure(figsize=(10, 6))

ax = sns.barplot(
    data=district_summary_sorted_time,
    x="total_time_spent_hrs",
    y=district_col
)

# Add value labels
for i, v in enumerate(district_summary_sorted_time["total_time_spent_hrs"]):
    ax.text(v + 0.1, i, f"{round(v, 1)}", va='center')

# Add horizontal lines
ax.yaxis.grid(True, linestyle='-', linewidth=1, alpha=0.3)
ax.xaxis.grid(False)

plt.title("Total Time Spent by District (Hours)")
plt.xlabel("Hours")
plt.ylabel("District Code")

plt.tight_layout()

chart2_path = output_folder / "time_spent_by_district.png"
plt.savefig(chart2_path)
plt.close()

print(f"📊 Saved: {chart2_path}")
