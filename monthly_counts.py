import pandas as pd

csv_path = r"V:\srm\wml\Workarea\ofedyshy\Projects\data-steward\gid_requests\GIS_Requests_2025_11_13.csv"
df = pd.read_csv(csv_path)

# --- Parse the compound date column into a single UTC datetime (_rcd) ---
parts = df['Requested Completion Date'].astype(str).str.split(';', n=1, expand=True)
left_date, right_iso = parts[0], parts[1]
chosen = right_iso.where(right_iso.notna() & (right_iso != ''), left_date)
df['_rcd'] = pd.to_datetime(chosen, utc=True, errors='coerce')

# --- Filter by staff and start date ---
staff_key = "Smith, Gail M FOR:EX,#Gail.Smith@gov.bc.ca"
start = pd.Timestamp('2025-06-01', tz='UTC')

df_filt = df[
    (df['GIS Staff Assigned'] == staff_key) &
    (df['_rcd'] >= start)
].copy()

# --- Monthly counts (start-of-month index). Include empty months if you want. ---
# Basic (only months that exist in data):
monthly = (
    df_filt
    .set_index('_rcd')
    .resample('MS')      # Month Start
    .size()
    .rename('Count')
)




# --- If you want to explicitly include zero-count months up to the last date in data: ---
if not df_filt.empty:
    idx = pd.date_range(start=start.normalize(), end=df_filt['_rcd'].max().normalize(), freq='MS', tz='UTC')
    monthly_full = monthly.reindex(idx, fill_value=0)
    print("\nWith zero-count months filled:")
    print(monthly_full)


# Convert to month names
monthly_named = monthly_full.copy()
monthly_named.index = monthly_named.index.strftime('%B')

print(monthly_named)