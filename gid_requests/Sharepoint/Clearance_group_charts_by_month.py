import pandas as pd
from pathlib import Path
import re
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import cm
from matplotlib.colors import Normalize

print("🚀 Script started")

# =========================
# INPUT
# =========================
file_path = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_10.csv")

if not file_path.exists():
    print("❌ File does NOT exist!")
    exit()

df = pd.read_csv(file_path)
print(f"✅ CSV loaded. Rows: {len(df)}")

# =========================
# REQUIRED COLUMNS
# =========================
title_col = "Title"
category_col = "Request Category"
date_col = "Request Submission Date"

required_cols = [title_col, category_col, date_col]
missing = [col for col in required_cols if col not in df.columns]

if missing:
    print(f"❌ Missing columns: {missing}")
    exit()

# =========================
# FILTER: ONLY CLEARANCE
# =========================
df[category_col] = df[category_col].fillna("").astype(str)
df = df[df[category_col].str.strip().str.lower() == "clearance"].copy()

print(f"✅ Rows after filtering 'Clearance': {len(df)}")

# =========================
# CLEAN DATA
# =========================
df[title_col] = df[title_col].fillna("").astype(str)
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

# Keep only rows with valid dates for charting
df = df[df[date_col].notna()].copy()
print(f"✅ Rows with valid dates: {len(df)}")

# =========================
# PATTERN DEFINITIONS
# =========================
pattern_defs = [
    ("Direct Sale", [
        r"\bD\d{5}\b"
    ]),
    ("Timber Auction", [
        r"\bTA\d{4}\b",
        r"\bTSL\b",
        r"TA\d{4}\b"
    ]),
    ("Road Permit", [
        r"\bR\d{5}\b",
        r"\bRP\b",
        r"\bRRS\b",
        r"\broad\w*\b",
        r"\bRd\b",
        r"\bRP\d{5}\b"
    ]),
    ("Forest Licence", [
        r"\bA\d{5}\b",
        r"\bCutting\s+Permit\b"
    ]),
    ("Tree Farm Licence", [
        r"\bTFL[^\w]?\S*"
    ]),
    ("Range", [
        r"\bRange\b",
        r"\bGrazing\b",
        r"\bRAN\d{6}\b"
    ]),
    ("BCTS", [
        r"\bBCTS\b"
    ]),
    ("Special Use Permit", [
        r"\bSpecial\s+Use\s+Permit\b",
        r"\bSUP\b",
        r"\bS\d{5}\b",
        r"\bS\d{5}\w*\b",
        r"S\d{5}\b"
    ]),
    ("Woodlot", [
        r"\bW\d{4}\b",
        r"\bWoodlot\b",
        r"\b\w*W\d{4}\b"
    ]),
    ("Free Use Permit", [
        r"\bFUP\b",
        r"\bFree\s+Use\s+Permit\b"
    ]),
    ("OLTC Licence to Cut", [
        r"\bL50032\b",
        r"\bOLTC\b",
        r"\bL\d{5}\b"
    ]),
    ("Water Line", [
        r"\bWater\s+Line\b"
    ]),
    ("Forest Service Road", [
        r"\bFSR\b",
        r"\bFSR\s*\d+\b",
        r"\b\d{4}\.\d{2}\b"
    ]),
    ("Forest and Range Practices Act", [
        r"\bFRPA\b"
    ]),
    ("Community Forest", [
        r"\bK0[A-Z]\b",
        r"\bK2S\b",
        r"\bK1P\b",
        r"\bN2K\b",
        r"\bK1C\b",
        r"\bN2B\b"
    ]),
    ("Wildfire Risk Reduction", [
        r"\bwildfire\s+risk\s+reduction\b",
        r"\bWRR\b",
        r"\bWRR\w*\b"
    ]),
    ("Timber Licence", [
        r"\bT0004\b",
        r"\bTL\b"
    ]),
    ("Forest Licence to Cut", [
        r"\bFLTC\b"
    ]),
    ("Map Notation", [
        r"\bMN\d{4}\b"
    ]),
    ("Recreation", [
        r"\bREC\d{4}\w*\b"
    ]),
    ("TFL", [
        r"\bTFL\b"
    ]),
]

# =========================
# CLASSIFICATION FUNCTION
# =========================
def classify_title(title: str) -> str:
    if not isinstance(title, str):
        title = ""

    text = title.strip()
    matches = []

    for category, patterns in pattern_defs:
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                matches.append((m.start(), m.end(), category))

    if matches:
        matches.sort(key=lambda x: (x[0], x[1]))
        return matches[0][2]

    if re.search(r"\bCP\s?\d+\b", text, flags=re.IGNORECASE):
        return "Forest Licence"

    return "Other"

# =========================
# APPLY CLASSIFICATION
# =========================
df["Title_Group"] = df[title_col].apply(classify_title)

# Merge duplicate TFL bucket into Tree Farm Licence
df["Title_Group"] = df["Title_Group"].replace({
    "TFL": "Tree Farm Licence"
})

print("✅ Classification complete")

# =========================
# PREPARE DATE RANGE
# =========================
df["month"] = df[date_col].dt.to_period("M").dt.to_timestamp()

start_month = df["month"].min()
end_month = df["month"].max()
all_months = pd.date_range(start=start_month, end=end_month, freq="MS")

print(f"✅ Chart range: {start_month.strftime('%Y-%m')} to {end_month.strftime('%Y-%m')}")

# =========================
# OUTPUT
# =========================
output_folder = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Charts")
output_folder.mkdir(parents=True, exist_ok=True)

charts_folder = output_folder / "clearance_group_charts"
charts_folder.mkdir(parents=True, exist_ok=True)

# =========================
# CHART STYLE
# =========================
sns.set(style="whitegrid")

def safe_filename(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", text).strip()

groups = sorted(df["Title_Group"].dropna().unique())

print(f"✅ Groups to chart: {len(groups)}")

# Store monthly summaries for one combined CSV
all_group_summaries = []

for group in groups:
    group_df = df[df["Title_Group"] == group].copy()

    monthly_summary = (
        group_df
        .groupby("month")
        .size()
        .reindex(all_months, fill_value=0)
        .reset_index()
    )

    monthly_summary.columns = ["month", "requests"]
    monthly_summary["month_label"] = monthly_summary["month"].dt.strftime("%b %Y")
    monthly_summary["Group"] = group

    # Save for combined CSV
    all_group_summaries.append(monthly_summary[["Group", "month", "month_label", "requests"]])

    values = monthly_summary["requests"]

    if values.min() == values.max():
        colors = [cm.get_cmap("Blues")(0.6)] * len(values)
    else:
        norm = Normalize(vmin=values.min(), vmax=values.max())
        cmap = cm.get_cmap("Blues")
        min_intensity = 0.35
        max_intensity = 0.85
        colors = [
            cmap(min_intensity + (max_intensity - min_intensity) * norm(v))
            for v in values
        ]

    plt.figure(figsize=(12, 6))

    ax = sns.barplot(
        data=monthly_summary,
        x="month_label",
        y="requests",
        palette=colors
    )

    # Add value labels on top of bars
    for i, v in enumerate(values):
        ax.text(
            i,
            v + 0.1,
            str(int(v)),
            ha="center",
            va="bottom",
            fontsize=9
        )

    ax.set_ylabel("")
    sns.despine(left=True)

    ax.yaxis.grid(True, linestyle="-", linewidth=1, alpha=0.3)
    ax.xaxis.grid(False)

    plt.title(group)
    plt.xlabel("Month")
    plt.ylabel("Number of Requests")
    plt.xticks(rotation=45)
    plt.tight_layout()

    chart_path = charts_folder / f"{safe_filename(group)}.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()

    print(f"📊 Saved: {chart_path}")

# =========================
# COMBINED MONTHLY SUMMARY CSV
# =========================
combined_monthly_df = pd.concat(all_group_summaries, ignore_index=True)

summary_wide_df = combined_monthly_df.pivot(
    index="Group",
    columns="month_label",
    values="requests"
).fillna(0).astype(int).reset_index()

# Add total column and sort by highest total
month_cols = [col for col in summary_wide_df.columns if col != "Group"]
summary_wide_df["Total"] = summary_wide_df[month_cols].sum(axis=1)
summary_wide_df = summary_wide_df.sort_values("Total", ascending=False).reset_index(drop=True)

summary_csv_path = output_folder / "clearance_group_monthly_summary.csv"
summary_wide_df.to_csv(summary_csv_path, index=False)

print(f"📁 Saved summary CSV: {summary_csv_path}")
print("🎉 Done")