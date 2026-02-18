# ua_trends_choropleth.py
# ------------------------------------------------------------
# Reads your Google Trends-by-region CSV, aggregates by (region, year),
# joins to Natural Earth admin-1 polygons for Ukraine, and exports a
# simple choropleth (darker = higher score, lighter = lower score).
#
# Usage examples (PowerShell):
#   python ua_trends_choropleth.py --year 2014 --language ua
#   python ua_trends_choropleth.py --year 2022 --language ru
# ------------------------------------------------------------

import argparse
import os
import re
import unicodedata
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt


# -----------------------------
# CONFIG (your paths)
# -----------------------------
CSV_PATH = r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Input\Geography_ua_trends_by_region_year_2011_2025.csv"     # Geography
#CSV_PATH = r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Input\Economy_ua_trends_by_region_year_2011_2025.csv"        # Economy
#CSV_PATH = r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Input\Government_ua_trends_by_region_year_2011_2025.csv"     # Government

GEO_DIR = r"V:\srm\wml\Workarea\ofedyshy\Scripts\League_Wedger\geo_data"
NE_ADMIN1 = os.path.join(GEO_DIR, "ne_10m_admin_1_states_provinces.shp")

OUT_DIR = r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Output"


# -----------------------------
# Helpers
# -----------------------------
def norm_text(s: str) -> str:
    """Normalize text for matching (lower, remove extra spaces/punct, keep apostrophes lightly)."""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s)
    # keep letters/numbers/apostrophes/spaces
    s = re.sub(r"[^\w\s'’\-]+", "", s, flags=re.UNICODE)
    return s


def build_region_mapping():
    """
    Map CSV 'region' (Ukrainian) -> Natural Earth iso_3166_2 code (UA-xx).

    Then you join like:
        agg_df["iso_3166_2"] = agg_df["region_norm"].map(mapping)
        admin1_gdf.merge(agg_df, on="iso_3166_2", how="left")
    """
    m = {
        "івано-франківська область": "UA-26",
        "волинська область": "UA-07",
        "вінницька область": "UA-05",
        "дніпропетровська область": "UA-12",
        "донецька область": "UA-14",
        "житомирська область": "UA-18",
        "закарпатська область": "UA-21",
        "запорізька область": "UA-23",
        "київська область": "UA-32",
        "кіровоградська область": "UA-35",
        "луганська область": "UA-09",   # matches your NE file
        "львівська область": "UA-46",
        "миколаївська область": "UA-48",
        "одеська область": "UA-51",
        "полтавська область": "UA-53",
        "рівненська область": "UA-56",
        "сумська область": "UA-59",
        "тернопільська область": "UA-61",
        "харківська область": "UA-63",
        "херсонська область": "UA-65",
        "хмельницька область": "UA-68",
        "черкаська область": "UA-71",
        "чернівецька область": "UA-77",
        "чернігівська область": "UA-74",
        "місто київ": "UA-30",

        # These are in your CSV but NOT present in the NE list you pasted:
        # (So they will remain NaN unless your shapefile actually has them)
        "крим": "UA-43",
        "місто севастополь": "UA-40",
        "місто севастополь.": "UA-40",  # handle trailing dot
    }

    # normalize keys (your script already has norm_text())
    return {norm_text(k): v for k, v in m.items()}



def find_best_ne_name(ne_names_norm, target_candidates):
    """
    Given normalized NE names and a list of candidate raw names, return the first that matches.
    """
    for cand in target_candidates:
        if norm_text(cand) in ne_names_norm:
            return cand
    return None


def load_and_aggregate(csv_path: str, year: int, language: str) -> pd.DataFrame:
    if language not in {"ua", "ru"}:
        raise ValueError("LANGUAGE must be 'ua' or 'ru'")

    df = pd.read_csv(csv_path)

    # Basic expected columns check
    needed = {"year", "region", "score_ua", "score_ru"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing expected columns: {sorted(missing)}")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[df["year"] == year].copy()

    score_col = "score_ua" if language == "ua" else "score_ru"
    df[score_col] = pd.to_numeric(df[score_col], errors="coerce")

    # Average across any word terms, only (region, year) matters
    out = (
        df.groupby(["region", "year"], as_index=False)[score_col]
          .mean()
          .rename(columns={score_col: "avg_score"})
    )

    out["region_norm"] = out["region"].map(norm_text)
    return out


def load_ukraine_admin1(ne_admin1_path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(ne_admin1_path)

    # Keep only Ukraine admin-1 polygons
    # Natural Earth typically uses: adm0_a3 == 'UKR' or admin == 'Ukraine'
    cols = set(gdf.columns)
    if "adm0_a3" in cols:
        gdf = gdf[gdf["adm0_a3"] == "UKR"].copy()
    elif "admin" in cols:
        gdf = gdf[gdf["admin"].str.lower() == "ukraine"].copy()
    else:
        raise ValueError("Could not find 'adm0_a3' or 'admin' column in the Natural Earth admin-1 file.")

    if "name" not in cols:
        raise ValueError("Natural Earth admin-1 file does not have a 'name' column (needed for joining).")

    gdf["name_norm"] = gdf["name"].map(norm_text)
    return gdf


def join_scores(admin1_gdf, agg_df):
    """
    Join aggregated scores to Natural Earth Ukraine admin-1 polygons using ISO codes.

    Expects:
      - admin1_gdf has column: 'iso_3166_2' (e.g., 'UA-71')
      - agg_df has columns: 'region_norm', 'avg_score' (from load_and_aggregate)

    Returns:
      GeoDataFrame with 'avg_score' joined in.
    """
    if "iso_3166_2" not in admin1_gdf.columns:
        raise ValueError(
            "admin1_gdf is missing 'iso_3166_2'. "
            "Inspect columns with: print(admin1_gdf.columns)"
        )

    mapping = build_region_mapping()  # returns {normalized_region_name: 'UA-xx'}

    agg_df = agg_df.copy()

    if "region_norm" not in agg_df.columns:
        # fallback: compute it if caller didn't
        if "region" not in agg_df.columns:
            raise ValueError("agg_df must contain 'region' or 'region_norm'.")
        agg_df["region_norm"] = agg_df["region"].map(norm_text)

    # Map CSV region -> ISO code
    agg_df["iso_3166_2"] = agg_df["region_norm"].map(mapping)

    # Warn about unmapped regions (non-fatal)
    unmapped = agg_df.loc[agg_df["iso_3166_2"].isna(), "region"].dropna().unique().tolist()
    if unmapped:
        print("\n[WARN] Unmapped CSV regions (no ISO code mapping found):")
        for r in sorted(unmapped):
            print(f"  - {r}")
        print("Add them to build_region_mapping() if needed.\n")

    # Merge on ISO code
    out = admin1_gdf.merge(
        agg_df[["iso_3166_2", "avg_score"]],
        how="left",
        on="iso_3166_2"
    )

    # If everything is missing, fail loudly (this is the 'all hatched' symptom)
    if out["avg_score"].notna().sum() == 0:
        # give a helpful hint about ISO codes present in the shapefile
        sample_iso = sorted(set(admin1_gdf["iso_3166_2"].dropna().astype(str)))[:25]
        raise ValueError(
            "Join produced 0 matched regions (all avg_score are NaN). "
            "Most likely the ISO codes in your shapefile differ from the mapping.\n"
            f"Sample iso_3166_2 codes in shapefile: {sample_iso}\n"
            "Check your mapping in build_region_mapping()."
        )

    # Optional: print match count for quick sanity check
    matched = out["avg_score"].notna().sum()
    total = len(out)
    print(f"[INFO] Joined scores to {matched} / {total} admin-1 polygons.")

    return out



def plot_choropleth(gdf: gpd.GeoDataFrame, year: int, language: str, out_png: str):
    # Ensure output folder exists
    os.makedirs(os.path.dirname(out_png), exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(9, 7))
    ax.set_axis_off()

    # Choropleth (darker = higher)
    gdf.plot(
        column="avg_score",
        ax=ax,
        legend=True,
        cmap="Greys",
        missing_kwds={
            "color": "lightgrey",
            "edgecolor": "white",
            "hatch": "///",
            "label": "No data",
        },
        linewidth=0.4,
        edgecolor="white",
    )

    lang_label = "Ukrainian term score" if language == "ua" else "Russian term score"
    ax.set_title(f"Ukraine Google Trends by Region — {lang_label} (avg), {year}", fontsize=12)

    # -----------------------------
    # Labels: write avg_score on each polygon
    # -----------------------------
    label_gdf = gdf[gdf["avg_score"].notna()].copy()
    if len(label_gdf) > 0:
        # point guaranteed inside polygon
        label_gdf["label_pt"] = label_gdf.geometry.representative_point()

        for _, row in label_gdf.iterrows():
            x = row["label_pt"].x
            y = row["label_pt"].y
            val = row["avg_score"]

            # Format: integers if close, else 1 decimal
            if pd.isna(val):
                continue
            if abs(val - round(val)) < 1e-9:
                txt = f"{int(round(val))}"
            else:
                txt = f"{val:.1f}"

            ax.text(
                x, y, txt,
                ha="center", va="center",
                fontsize=7,
                color="black",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.65),
                zorder=5
            )

    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close(fig)



def main():
    year = 2011         #<-------------------------------------------------------------------------------------------YEAR
    language = "ua"     #<-- ua or ru
    category = "geography"           #<-- economy, geography, government

    agg = load_and_aggregate(CSV_PATH, year, language)
    ukr = load_ukraine_admin1(NE_ADMIN1)
    joined = join_scores(ukr, agg)

    out_png = os.path.join(OUT_DIR, f"ua_trends_{category}_{language}_{year}.png")
    out_csv = os.path.join(OUT_DIR, f"ua_trends_{category}_{language}_{year}_avg_by_region.csv")

    os.makedirs(OUT_DIR, exist_ok=True)
    agg[["region", "year", "avg_score"]].to_csv(out_csv, index=False, encoding="utf-8-sig")
    plot_choropleth(joined, year, language, out_png)

    print(f"Saved:\n  {out_csv}\n  {out_png}")



if __name__ == "__main__":
    main()
