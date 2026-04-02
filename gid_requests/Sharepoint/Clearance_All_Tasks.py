import pandas as pd
from pathlib import Path

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
category_col = "Request Category"
date_col = "Request Submission Date"

required_cols = [category_col, date_col]
missing = [col for col in required_cols if col not in df.columns]

if missing:
    print(f"❌ Missing columns: {missing}")
    exit()

# =========================
# CLEAN DATA
# =========================
df[category_col] = df[category_col].fillna("").astype(str)
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

# =========================
# FILTER
# =========================
filtered_df = df[
    (df[category_col].str.strip().str.lower() == "clearance") &
    (df[date_col].dt.month == 3)
].copy()

print(f"✅ Filtered rows (Clearance in March): {len(filtered_df)}")

# =========================
# OUTPUT
# =========================
output_folder = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs")
output_folder.mkdir(parents=True, exist_ok=True)

output_path = output_folder / "clearance_requests_march.csv"

filtered_df.to_csv(output_path, index=False)

print(f"📁 Saved: {output_path}")
print("🎉 Done")