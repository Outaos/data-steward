import pandas as pd

# path to your CSV
csv_path = r"V:\srm\wml\Workarea\ofedyshy\Projects\data-steward\gid_requests\GIS_Requests_2025_11_13.csv"

# read the data frame
df = pd.read_csv(csv_path)

# Split the compound date into two parts: plain date (left) and ISO datetime (right)
parts = df['Requested Completion Date'].astype(str).str.split(';', n=1, expand=True)
left_date  = parts[0]             # e.g., 2025-11-10
right_iso  = parts[1]             # e.g., 2025-11-10T08:00:00Z (may be NaN)

# Prefer the ISO datetime when available, otherwise use the left date
chosen = right_iso.where(right_iso.notna() & (right_iso != ''), left_date)

# Parse to datetime (UTC-aware if the right side has Z). Coerce invalids to NaT.
df['_rcd'] = pd.to_datetime(chosen, utc=True, errors='coerce')

# show first five rows
#print(df.head())

# show all column names
print("Fields:")
for field in df.columns:
    print(" -", field) 

# Group by Staff and Category, count how many requests in each
grouped = df.groupby(['GIS Staff Assigned']).size().reset_index(name='Count')

# sort values
grouped = grouped.sort_values(by='Count', ascending=False)

print(grouped)

print("------------------------------------------")


# 🔹 Define date range
start_date = pd.Timestamp('2025-06-01', tz='UTC')
end_date   = pd.Timestamp('2025-08-30', tz='UTC')

# 🔹 Filter rows within range (inclusive)
filtered = df[(df['_rcd'] >= start_date) & (df['_rcd'] <= end_date)]

# Group by staff and count
grouped = (
    filtered.groupby(['GIS Staff Assigned'])
    .size()
    .reset_index(name='Count')
    .sort_values('Count', ascending=False)
)

print(grouped)