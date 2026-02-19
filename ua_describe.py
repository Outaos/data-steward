import geopandas as gpd
import os

# ua_trends_country_barchart.py
# ------------------------------------------------------------
# Reads Google Trends-by-region CSV and produces a country-level
# yearly bar chart (avg across all regions & all terms).
#
# Usage examples (PowerShell):
#   python ua_trends_country_barchart.py --category geography --language ua
#   python ua_trends_country_barchart.py --csv "...\Economy_ua_trends_by_region_year_2011_2025.csv" --language ru
# ------------------------------------------------------------

import argparse
import os
import re
import unicodedata
import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------
# Defaults (edit if you want)
# -----------------------------
DEFAULT_CSVS = {
    "geography": r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Input\Geography_ua_trends_by_region_year_2011_2025.csv",
    "economy":   r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Input\Economy_ua_trends_by_region_year_2011_2025.csv",
    "government":r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Input\Government_ua_trends_by_region_year_2011_2025.csv",
}

OUT_DIR = r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Output"


# -----------------------------
# Helpers
# -----------------------------
def norm_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s'’\-]+", "", s, flags=re.UNICODE)
    return s


def load_country_yearly_avg(
    csv_path: str,
    language: str,
    year_min: int | None = None,
    year_max: int | None = None,
    exclude_regions: list[str] | None = None,
) -> pd.DataFrame:
    if language not in {"ua", "ru"}:
        raise ValueError("language must be 'ua' or 'ru'")

    df = pd.read_csv(csv_path)

    needed = {"year", "region", "score_ua", "score_ru"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing expected columns: {sorted(missing)}")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    score_col = "score_ua" if language == "ua" else "score_ru"
    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")

    if exclude_regions:
        ex_norm = {norm_text(x) for x in exclude_regions}
        df["region_norm"] = df["region"].map(norm_text)
        df = df[~df["region_norm"].isin(ex_norm)].copy()

    if year_min is not None:
        df = df[df["year"] >= year_min].copy()
    if year_max is not None:
        df = df[df["year"] <= year_max].copy()

    out = (
        df.groupby("year", as_index=False)[score_col]
          .mean()
          .rename(columns={score_col: "country_avg_score"})
          .sort_values("year")
    )

    # sanity check
    if out["country_avg_score"].notna().sum() == 0:
        raise ValueError("All country_avg_score values are NaN. Check your input CSV / score columns.")

    return out


def plot_country_barchart(df_year: pd.DataFrame, language: str, title: str, out_png: str):
    os.makedirs(os.path.dirname(out_png), exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 5))

    years = df_year["year"].astype(int).tolist()
    vals = df_year["country_avg_score"].tolist()

    ax.bar(years, vals)

    ax.set_xlabel("Year")
    ax.set_ylabel("Average Google Trends score")
    ax.set_title(title)

    # make yearly ticks readable
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha="right")

    # optional: put values on top if you like (comment out if noisy)
    for x, v in zip(years, vals):
        if pd.isna(v):
            continue
        ax.text(x, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close(fig)


def main():
    # -------------------------------------------------
    # SETTINGS (edit these directly)
    # -------------------------------------------------
    category = "geography"   # "geography", "economy", "government"
    language = "ua"          # "ua" or "ru"
    year_min = 2011
    year_max = 2025
    exclude_crimea = False
    out_dir = OUT_DIR
    # -------------------------------------------------

    csv_path = DEFAULT_CSVS[category]

    exclude = None
    if exclude_crimea:
        exclude = ["Крим", "місто Севастополь", "місто Севастополь."]

    df_year = load_country_yearly_avg(
        csv_path=csv_path,
        language=language,
        year_min=year_min,
        year_max=year_max,
        exclude_regions=exclude,
    )

    os.makedirs(out_dir, exist_ok=True)

    out_csv = os.path.join(
        out_dir,
        f"ua_trends_{category}_{language}_country_yearly_avg.csv"
    )
    out_png = os.path.join(
        out_dir,
        f"ua_trends_{category}_{language}_country_yearly_avg.png"
    )

    df_year.to_csv(out_csv, index=False, encoding="utf-8-sig")

    lang_label = "Ukrainian term score" if language == "ua" else "Russian term score"
    title = f"Ukraine Google Trends — country avg by year ({lang_label})"

    if exclude_crimea:
        title += " [excluding Crimea/Sevastopol]"

    plot_country_barchart(df_year, language, title, out_png)

    print(f"Saved:\n  {out_csv}\n  {out_png}")



if __name__ == "__main__":
    main()




"""


WEST
        "івано-франківська область": "UA-26",
        "волинська область": "UA-07",
        "закарпатська область": "UA-21",
        "львівська область": "UA-46",
        "рівненська область": "UA-56",
        "тернопільська область": "UA-61",
        "чернівецька область": "UA-77",
RIGHT_BANK
        "вінницька область": "UA-05",
        "житомирська область": "UA-18",
        "київська область": "UA-32",
        "кіровоградська область": "UA-35",
        "хмельницька область": "UA-68",
        "черкаська область": "UA-71",
        "місто київ": "UA-30",
LEFT_BANK
        "полтавська область": "UA-53",
        "сумська область": "UA-59",
        "чернігівська область": "UA-74",
SOUTH
        "миколаївська область": "UA-48",
        "одеська область": "UA-51",
        "херсонська область": "UA-65",

EAST
        "дніпропетровська область": "UA-12",
        "донецька область": "UA-14",
        "запорізька область": "UA-23",
        "луганська область": "UA-09",   # matches your NE file
        "харківська область": "UA-63",
CRIMEA
        "крим": "UA-43",
        "місто севастополь": "UA-40",
        "місто севастополь.": "UA-40", 

"""


# ---- PATH ----
GEO_DIR = r"V:\srm\wml\Workarea\ofedyshy\Scripts\League_Wedger\geo_data"
NE_ADMIN1 = os.path.join(GEO_DIR, "ne_10m_admin_1_states_provinces.shp")

# ---- Load ----
gdf = gpd.read_file(NE_ADMIN1)

print("\nALL COLUMNS:\n")
print(list(gdf.columns))

print("\n-----------------------------------\n")

# Filter to Ukraine only
if "adm0_a3" in gdf.columns:
    ukr = gdf[gdf["adm0_a3"] == "RUS"].copy()   # UKR
elif "admin" in gdf.columns:
    ukr = gdf[gdf["admin"].str.lower() == "russia"].copy()  #ukraine
else:
    raise ValueError("Could not detect country column.")

print(f"Total Ukraine admin-1 regions found: {len(ukr)}\n")

# Choose useful columns if present
cols_to_show = []

for c in ["name", "name_en", "iso_3166_2", "gn_name", "type", "region"]:
    if c in ukr.columns:
        cols_to_show.append(c)

if not cols_to_show:
    cols_to_show = ["name"]

print("Relevant columns for joining:\n")
print(ukr[cols_to_show].sort_values("name").to_string(index=False))

print("\nUnique name values:\n")
print(sorted(ukr["name"].unique()))
