import pandas as pd
from pathlib import Path
import re

print("🚀 Script started")

# =========================
# INPUT
# =========================
file_path = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_02.csv")

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
created_by_col = "Created By"

required_cols = [title_col, category_col, created_by_col]
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
df[created_by_col] = df[created_by_col].fillna("Unknown").astype(str).str.strip()
df.loc[df[created_by_col] == "", created_by_col] = "Unknown"

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

print("✅ Classification complete")

# Merge TFL into Tree Farm Licence
df["Title_Group"] = df["Title_Group"].replace({
    "TFL": "Tree Farm Licence"
})

# =========================
# SUMMARY BY GROUP + CREATED BY
# =========================
created_by_summary = pd.crosstab(df["Title_Group"], df[created_by_col])

created_by_summary["Total"] = created_by_summary.sum(axis=1)
created_by_summary = created_by_summary.reset_index()

grand_total = created_by_summary["Total"].sum()
created_by_summary["Percent"] = (created_by_summary["Total"] / grand_total * 100).round(1)
created_by_summary["Percent"] = created_by_summary["Percent"].astype(str) + "%"

base_cols = ["Title_Group", "Total", "Percent"]
# Get totals per person (before reset_index is easiest, but we can do it here)
person_totals = created_by_summary.drop(columns=["Title_Group", "Total", "Percent"]).sum()
# Sort persons by total descending
person_cols = person_totals.sort_values(ascending=False).index.tolist()

created_by_summary = created_by_summary[["Title_Group", "Total", "Percent"] + person_cols]
created_by_summary = created_by_summary.sort_values("Total", ascending=False).reset_index(drop=True)
created_by_summary = created_by_summary.rename(columns={"Title_Group": "Group"})

print("\n📊 Summary by Group and Created By:")
print(created_by_summary.to_string(index=False))

# =========================
# EXPORT OTHER ROWS
# =========================
other_df = df[df["Title_Group"] == "Other"].copy()

# =========================
# OUTPUT
# =========================
output_folder = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs")
output_folder.mkdir(parents=True, exist_ok=True)

summary_path = output_folder / "Clearance_pattern_summary_by_Client.csv"
other_path = output_folder / "Clearance_pattern_other_rows.csv"

created_by_summary.to_csv(summary_path, index=False)
other_df.to_csv(other_path, index=False)

print(f"\n📁 Saved summary: {summary_path}")
print(f"📁 Saved 'Other' rows: {other_path}")
print(f"ℹ️ Rows in 'Other': {len(other_df)}")
print("🎉 Done")