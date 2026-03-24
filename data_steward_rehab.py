import pandas as pd
from pathlib import Path

print("🚀 Script started")

# =========================
# INPUT FILE
# =========================
file_path = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Projects\data-steward\gid_requests\GIS_Requests_2026_03_24.csv")
print(f"📂 Checking input file: {file_path}")

if not file_path.exists():
    print("❌ File does NOT exist!")
    exit()
else:
    print("✅ File exists")

# =========================
# READ FILE
# =========================
print("📖 Reading CSV...")
df = pd.read_csv(file_path)
print(f"✅ CSV loaded. Rows: {len(df)}, Columns: {len(df.columns)}")
print(f"Columns: {list(df.columns)}")

# =========================
# COLUMN NAMES
# =========================
title_col = "Title"
time_col = "Time Spent (hrs)"
district_col = "District Code"
date_col = "GIS Completion Date"

print("🔍 Checking required columns...")

required_cols = [title_col, time_col, district_col, date_col]
missing = [col for col in required_cols if col not in df.columns]

if missing:
    print(f"❌ Missing columns: {missing}")
    exit()
else:
    print("✅ All required columns found")

# =========================
# CLEAN / PREP
# =========================
print("🧹 Cleaning data...")

df[title_col] = df[title_col].fillna("").astype(str)
df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0)
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

print("✅ Data cleaned")

# =========================
# FILTER LOGIC
# =========================
print("🔎 Applying filter...")

pattern = r"\b(?:K\d{5}|N\d{5}|C\d{5})\b|rehab"
mask = df[title_col].str.contains(pattern, case=False, na=False, regex=True)

matched_df = df[mask].copy()

print(f"✅ Filter applied. Matches found: {len(matched_df)}")

# =========================
# OUTPUT FOLDER
# =========================
output_folder = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Projects\data-steward\gid_requests\Output")
print(f"📁 Output folder: {output_folder}")

try:
    output_folder.mkdir(parents=True, exist_ok=True)
    print("✅ Output folder ready")
except Exception as e:
    print(f"❌ Failed to create/access output folder: {e}")
    exit()

# =========================
# SAVE OUTPUTS
# =========================
print("💾 Saving files...")

try:
    matched_df.to_csv(output_folder / "matched_titles.csv", index=False)
    print("✅ matched_titles.csv saved")

    district_summary = (
        matched_df
        .groupby(district_col, dropna=False)
        .agg(
            matching_rows=(title_col, "size"),
            total_time_spent_hrs=(time_col, "sum")
        )
        .reset_index()
    )

    district_summary.to_csv(output_folder / "summary_by_district_code.csv", index=False)
    print("✅ summary_by_district_code.csv saved")

    date_summary = (
        matched_df
        .assign(**{date_col: matched_df[date_col].dt.date})
        .groupby(date_col, dropna=False)
        .agg(
            matching_rows=(title_col, "size"),
            total_time_spent_hrs=(time_col, "sum")
        )
        .reset_index()
    )

    date_summary.to_csv(output_folder / "summary_by_gis_completion_date.csv", index=False)
    print("✅ summary_by_gis_completion_date.csv saved")

except Exception as e:
    print(f"❌ Error while saving: {e}")
    exit()

print("🎉 Script finished successfully")