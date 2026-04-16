import os
import pandas as pd
import matplotlib.pyplot as plt

# --- INPUTS ---
csv_path = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\GIS_Requests_2026_04_16.csv"

output_folder = r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\SHAREPOINT_STATS\Rehab_stats\Outputs\Team_Members"
charts_folder = os.path.join(output_folder, "8_Completed_tasks_per_month_charts")

output_csv = os.path.join(output_folder, "_8_Completed_tasks_per_month.csv")

start_date = pd.Timestamp("2025-07-01")

# --- CREATE OUTPUT FOLDER FOR CHARTS ---
os.makedirs(charts_folder, exist_ok=True)

# --- LOAD CSV ---
df = pd.read_csv(csv_path)

# --- FILTER ---
df = df[
    (df["Request Status"] == "Completed") &
    (df["GIS Staff Assigned"].notna()) &
    (df["GIS Completion Date"].notna()) &
    (df["Request Category"].notna())
].copy()

# --- DATE FIELD ---
df["GIS Completion Date"] = pd.to_datetime(df["GIS Completion Date"], errors="coerce")
df = df[df["GIS Completion Date"].notna()].copy()

# --- START DATE FILTER ---
df = df[df["GIS Completion Date"] >= start_date].copy()

# --- CATEGORY GROUPING ---
def map_category_group(val):
    val = str(val).strip()

    if val == "Clearance":
        return "Clearance"
    elif val in ["General Mapping", "Web Mapping", "Data Request", "Training"]:
        return "General Mapping"
    elif val == "Spatial Analysis":
        return "Spatial Analysis"
    else:
        return None

df["Category Group"] = df["Request Category"].apply(map_category_group)
df = df[df["Category Group"].notna()].copy()

# Ensure unique tasks per staff
df_unique = df.drop_duplicates(subset=["GIS Staff Assigned", "ID"]).copy()

# --- YEAR-MONTH FIELDS ---
df_unique["YearMonthPeriod"] = df_unique["GIS Completion Date"].dt.to_period("M")
df_unique["YearMonth"] = df_unique["YearMonthPeriod"].astype(str)

# --- GROUPED CSV OUTPUT ---
grouped_csv = (
    df_unique.groupby(["GIS Staff Assigned", "YearMonth", "Category Group"])
    .agg(Completed_Tasks=("ID", "nunique"))
    .reset_index()
    .sort_values(by=["GIS Staff Assigned", "YearMonth", "Category Group"])
)

grouped_csv.to_csv(output_csv, index=False)

# --- CHART PREP ---
category_order = ["Clearance", "General Mapping", "Spatial Analysis"]

all_months = pd.period_range(
    start=start_date.to_period("M"),
    end=df_unique["YearMonthPeriod"].max(),
    freq="M"
)

def make_safe_filename(text):
    return "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in str(text)).strip()

# --- CHART FOR EACH GIS STAFF ---
staff_list = sorted(df_unique["GIS Staff Assigned"].unique())

for staff in staff_list:
    staff_df = df_unique[df_unique["GIS Staff Assigned"] == staff].copy()

    chart_df = (
        staff_df.groupby(["YearMonthPeriod", "Category Group"])
        .agg(Completed_Tasks=("ID", "nunique"))
        .reset_index()
    )

    pivot_df = chart_df.pivot(
        index="YearMonthPeriod",
        columns="Category Group",
        values="Completed_Tasks"
    ).reindex(all_months, fill_value=0)

    for col in category_order:
        if col not in pivot_df.columns:
            pivot_df[col] = 0

    pivot_df = pivot_df[category_order]

    x = range(len(pivot_df))

    clearance_vals = pivot_df["Clearance"].values
    general_vals = pivot_df["General Mapping"].values
    spatial_vals = pivot_df["Spatial Analysis"].values

    month_labels = [p.strftime("%B") for p in pivot_df.index]
    year_values = [p.year for p in pivot_df.index]

    plt.figure(figsize=(16, 6))

    # Stacked bars
    plt.bar(x, clearance_vals, label="Clearance")
    plt.bar(x, general_vals, bottom=clearance_vals, label="General Mapping")
    plt.bar(x, spatial_vals, bottom=clearance_vals + general_vals, label="Spatial Analysis")

    # Value labels inside each segment
    for i in range(len(pivot_df)):
        c_val = clearance_vals[i]
        g_val = general_vals[i]
        s_val = spatial_vals[i]

        if c_val > 0:
            plt.text(i, c_val / 2, str(int(c_val)), ha="center", va="center", fontsize=8, color="white")
        if g_val > 0:
            plt.text(i, c_val + g_val / 2, str(int(g_val)), ha="center", va="center", fontsize=8, color="white")
        if s_val > 0:
            plt.text(i, c_val + g_val + s_val / 2, str(int(s_val)), ha="center", va="center", fontsize=8, color="white")

    # X-axis months
    plt.xticks(list(x), month_labels, rotation=0, fontsize=9)

    # Year labels centered under month ranges
    year_positions = {}
    for idx, yr in enumerate(year_values):
        year_positions.setdefault(yr, []).append(idx)

    ax = plt.gca()
    y_min, y_max = ax.get_ylim()
    year_text_y = -0.12 * y_max

    for yr, positions in year_positions.items():
        center_pos = sum(positions) / len(positions)
        plt.text(center_pos, year_text_y, str(yr), ha="center", va="top", fontsize=9)

        # Optional vertical separator between years
        if positions[-1] < len(year_values) - 1:
            ax.axvline(positions[-1] + 0.5, linestyle=":", linewidth=1)

    plt.title(f"Completed Tasks per Month\n{staff}", fontsize=18)
    plt.ylabel("Number of Tasks", fontsize=12)
    plt.xlabel("")
    plt.legend(title="Category Group", ncol=3, loc="upper left")
    plt.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()

    safe_name = make_safe_filename(staff)
    chart_path = os.path.join(charts_folder, f"{safe_name}_completed_tasks_per_month.png")

    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

print(f"CSV saved to:\n{output_csv}")
print(f"Charts saved to:\n{charts_folder}")