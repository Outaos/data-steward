import pandas as pd
from pathlib import Path

file_path = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Projects\data-steward\gid_requests\GIS_Requests_2026_03_24.csv")

df = pd.read_csv(file_path)

title_col = "Title"
creator_col = "GIS Staff Assigned" #"Created By"

# Clean columns
df[title_col] = df[title_col].fillna("").astype(str)
df[creator_col] = df[creator_col].fillna("").astype(str).str.strip()

# Rehab filter
pattern = r"\b(?:K\d{5}|N\d{5}|C\d{5})\b|rehab"
include_mask = df[title_col].str.contains(pattern, case=False, na=False, regex=True)
exclude_mask = df[title_col].str.contains(r"BARC", case=False, na=False)

matched_df = df[include_mask & ~exclude_mask].copy()

# Count per person
counts = matched_df[creator_col].value_counts()

# Print results
for person, count in counts.items():
    print(f"{person}: {count}")