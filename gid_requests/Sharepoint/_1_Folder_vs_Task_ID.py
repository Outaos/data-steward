import os
import pandas as pd

# --- INPUTS ---
csv_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_16.csv"

folder_2025 = r"\\spatialfiles.bcgov\Work\for\RSI\SA\Tasks\2025"
folder_2026 = r"\\spatialfiles.bcgov\Work\for\RSI\SA\Tasks\2026"

output_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Team_Members\_1_Folder_vs_Task_ID.csv"

# --- LOAD CSV ---
df = pd.read_csv(csv_path)
df["ID"] = df["ID"].astype(str)

# --- GET ALL FOLDERS ---
def get_folder_names(folder_path):
    try:
        return {
            name for name in os.listdir(folder_path)
            if os.path.isdir(os.path.join(folder_path, name))
        }
    except Exception as e:
        print(f"Error accessing {folder_path}: {e}")
        return set()

folders_2025 = get_folder_names(folder_2025)
folders_2026 = get_folder_names(folder_2026)
all_folders = folders_2025.union(folders_2026)

# --- RESULTS STORAGE ---
results = []

# --- LOOP THROUGH STAFF ---
staff_list = df["GIS Staff Assigned"].dropna().unique()

for staff in sorted(staff_list):
    df_staff = df[df["GIS Staff Assigned"] == staff]
    staff_ids = set(df_staff["ID"])

    if len(staff_ids) == 0:
        continue

    ids_with_folder = staff_ids.intersection(all_folders)

    total_ids = len(staff_ids)
    match_count = len(ids_with_folder)

    percent = (match_count / total_ids * 100) if total_ids > 0 else 0

    # --- PRINT (as requested) ---
    print(f"{staff} -> Folders created: {match_count} ({percent:.2f}%)")

    # --- STORE FOR CSV ---
    results.append({
        "GIS Staff Assigned": staff,
        "Total Tasks": total_ids,
        "Folders Created": match_count,
        "Percent (%)": round(percent, 2)
    })

# --- SAVE CSV ---
df_out = pd.DataFrame(results)
df_out = df_out.sort_values(by="Percent (%)", ascending=False)

df_out.to_csv(output_path, index=False)

print(f"\nOutput saved to:\n{output_path}")