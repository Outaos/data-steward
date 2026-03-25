import pandas as pd
from pathlib import Path

file_path = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Projects\data-steward\gid_requests\GIS_Requests_2026_03_24.csv")

df = pd.read_csv(file_path)

creator_col = "Created By"

# Clean column
df[creator_col] = df[creator_col].fillna("").astype(str).str.strip()

# Count requests per person
counts = df[creator_col].value_counts()

# Print results
for person, count in counts.items():
    print(f"{person}: {count}")