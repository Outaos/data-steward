import os
import numpy as np
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
    elif val in ["General Mapping", "Web Mapping", "Data Request", "Training", "Spatial Analysis"]:
        return "Analytical & Mapping Tasks"
    else:
        return None

df["Category Group"] = df["Request Category"].apply(map_category_group)
df = df[df["Category Group"].notna()].copy()

# --- ENSURE UNIQUE TASKS PER STAFF ---
df_unique = df.drop_duplicates(subset=["GIS Staff Assigned", "ID"]).copy()

# --- YEAR-MONTH FIELDS ---
df_unique["YearMonthPeriod"] = df_unique["GIS Completion Date"].dt.to_period("M")
df_unique["YearMonth"] = df_unique["YearMonthPeriod"].dt.strftime("%b-%y")

# --- GROUPED DATA FOR CSV ---
grouped_csv = (
    df_unique.groupby(["GIS Staff Assigned", "YearMonthPeriod", "YearMonth", "Category Group"])
    .agg(Completed_Tasks=("ID", "nunique"))
    .reset_index()
    .sort_values(by=["GIS Staff Assigned", "YearMonthPeriod", "Category Group"])
)

# Save CSV without helper period column
grouped_csv.drop(columns=["YearMonthPeriod"]).to_csv(output_csv, index=False)

# --- CHART SETTINGS ---
category_order = ["Analytical & Mapping Tasks", "Clearance"]

# light blue + dark blue
category_colors = {
    "Analytical & Mapping Tasks": "#1F4E79",
    "Clearance":  "#5B9BD5"
}

all_months = pd.period_range(
    start=start_date.to_period("M"),
    end=grouped_csv["YearMonthPeriod"].max(),
    freq="M"
)

def make_safe_filename(text):
    return "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in str(text)).strip()

# --- CHART FOR EACH GIS STAFF ---
staff_list = sorted(grouped_csv["GIS Staff Assigned"].unique())

for staff in staff_list:
    staff_grouped = grouped_csv[grouped_csv["GIS Staff Assigned"] == staff].copy()

    # build pivot DIRECTLY from grouped CSV-ready data
    pivot_df = (
        staff_grouped.pivot_table(
            index="YearMonthPeriod",
            columns="Category Group",
            values="Completed_Tasks",
            aggfunc="sum",
            fill_value=0
        )
        .reindex(all_months, fill_value=0)
    )

    for col in category_order:
        if col not in pivot_df.columns:
            pivot_df[col] = 0

    pivot_df = pivot_df[category_order]

    x = np.arange(len(pivot_df))
    month_labels = [p.strftime("%b") for p in pivot_df.index]
    year_values = [p.year for p in pivot_df.index]

    analytical_vals = pivot_df["Analytical & Mapping Tasks"].to_numpy()
    clearance_vals = pivot_df["Clearance"].to_numpy()

    fig, ax = plt.subplots(figsize=(16, 6))

    # stacked bars
    ax.bar(
        x,
        analytical_vals,
        label="Analytical & Mapping Tasks",
        color=category_colors["Analytical & Mapping Tasks"]
    )
    ax.bar(
        x,
        clearance_vals,
        bottom=analytical_vals,
        label="Clearance",
        color=category_colors["Clearance"]
    )

    # value labels
    for i in range(len(pivot_df)):
        a_val = analytical_vals[i]
        c_val = clearance_vals[i]

        if a_val > 0:
            ax.text(
                i, a_val / 2, str(int(a_val)),
                ha="center", va="center", fontsize=8, color="white"
            )
        if c_val > 0:
            ax.text(
                i, a_val + c_val / 2, str(int(c_val)),
                ha="center", va="center", fontsize=8, color="white"
            )

    # axes
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels, fontsize=10)
    ax.set_xlim(-0.5, len(x) - 0.5)
    ax.set_ylabel("Number of Tasks", fontsize=12)
    ax.set_title(f"Completed Tasks per Month\n{staff}", fontsize=20)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.legend(title="Category Group", ncol=2, loc="upper left")

    # year labels and separators
    ymin, ymax = ax.get_ylim()
    year_text_y = -0.12 * ymax

    year_positions = {}
    for idx, yr in enumerate(year_values):
        year_positions.setdefault(yr, []).append(idx)

    for yr, positions in year_positions.items():
        center_pos = sum(positions) / len(positions)
        ax.text(center_pos, year_text_y, str(yr), ha="center", va="top", fontsize=10)

        if positions[-1] < len(year_values) - 1:
            ax.axvline(positions[-1] + 0.5, linestyle=":", linewidth=1, color="gray")

    plt.tight_layout()

    safe_name = make_safe_filename(staff)
    chart_path = os.path.join(charts_folder, f"{safe_name}_completed_tasks_per_month.png")
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

print(f"CSV saved to:\n{output_csv}")
print(f"Charts saved to:\n{charts_folder}")