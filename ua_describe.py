import geopandas as gpd
import os

# ---- PATH ----
GEO_DIR = r"V:\srm\wml\Workarea\ofedyshy\Scripts\League_Wedger\geo_data"
NE_ADMIN1 = os.path.join(GEO_DIR, "ne_10m_admin_1_states_provinces.shp")

# ---- Load ----
gdf = gpd.read_file(NE_ADMIN1)

print("\nALL COLUMNS:\n")
print(list(gdf.columns))

print("\n-----------------------------------\n")

# Filter to Russia only
if "adm0_a3" in gdf.columns:
    rus = gdf[gdf["adm0_a3"] == "RUS"].copy()
elif "admin" in gdf.columns:
    rus = gdf[gdf["admin"].str.lower() == "russia"].copy()
else:
    raise ValueError("Could not detect country column.")

print(f"Total Russia admin-1 regions found: {len(rus)}\n")

# Show potentially useful join columns
cols_to_show = []

for c in ["name", "name_en", "iso_3166_2", "gn_name", "type", "region"]:
    if c in rus.columns:
        cols_to_show.append(c)

if not cols_to_show:
    cols_to_show = ["name"]

print("Relevant columns for joining:\n")
print(rus[cols_to_show].sort_values("name").to_string(index=False))

print("\nUnique name values:\n")
print(sorted(rus["name"].unique()))
