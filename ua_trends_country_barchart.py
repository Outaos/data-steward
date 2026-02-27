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
    "common_words":r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Input\Common_words_ua_trends_by_region_year_2011_2025.csv",
}

OUT_DIR = r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang\Output\Charts"


# -----------------------------
# Area presets (CSV region names)
# -----------------------------
AREA_REGIONS = {
    "ALL": [],  # special-case: no filtering
    "WEST": [
        "івано-франківська область",
        "волинська область",
        "закарпатська область",
        "львівська область",
        "рівненська область",
        "тернопільська область",
        "чернівецька область",
    ],
    "RIGHT_BANK": [
        "вінницька область",
        "житомирська область",
        "київська область",
        "кіровоградська область",
        "хмельницька область",
        "черкаська область",
        "місто київ",
    ],
    "LEFT_BANK": [
        "полтавська область",
        "сумська область",
        "чернігівська область",
    ],
    "SOUTH": [
        "миколаївська область",
        "одеська область",
        "херсонська область",
    ],
    "EAST": [
        "дніпропетровська область",
        "донецька область",
        "запорізька область",
        "харківська область",
    ],
    "OCCUPIED_TERRITORY": [
        "крим",
        "місто севастополь",
        "місто севастополь.",
        "луганська область",
    ],
    "KYIV": [
        "місто київ",
    ],
    "TERNOPIL": [
        "тернопільська область",
    ],
    "MYKOLAJIV": [
        "миколаївська область",
    ],
}

def get_area_region_norms(area: str) -> set[str]:
    area = (area or "ALL").strip().upper()
    if area not in AREA_REGIONS:
        raise ValueError(f"Unknown area '{area}'. Choose one of: {sorted(AREA_REGIONS.keys())}")
    return {norm_text(x) for x in AREA_REGIONS[area]}

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
    area: str = "ALL",   # <--- NEW
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

    # Normalize region once (used by both filters)
    df["region_norm"] = df["region"].map(norm_text)

    # (A) optional explicit region exclusions (e.g., Crimea)
    if exclude_regions:
        ex_norm = {norm_text(x) for x in exclude_regions}
        df = df[~df["region_norm"].isin(ex_norm)].copy()

    # (B) optional AREA filter
    area = (area or "ALL").strip().upper()
    if area != "ALL":
        allowed = get_area_region_norms(area)
        df = df[df["region_norm"].isin(allowed)].copy()

        # helpful warning if your CSV spelling doesn't match presets
        found = set(df["region_norm"].unique())
        missing_in_csv = sorted(allowed - found)
        if missing_in_csv:
            print("\n[WARN] These area regions were not found in the CSV after normalization:")
            for r in missing_in_csv:
                print(f"  - {r}")
            print("Check spelling in AREA_REGIONS vs your CSV 'region' column.\n")

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

    if out["country_avg_score"].notna().sum() == 0:
        raise ValueError("All country_avg_score values are NaN. Check your input CSV / score columns / filters.")

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
    category = "common_words"   # geography, economy, government
    language = "ua"          # ua or ru
    year_min = 2011
    year_max = 2025

    area = "MYKOLAJIV"             # ALL, WEST, RIGHT_BANK, LEFT_BANK, SOUTH, EAST, OCCUPIED_TERRITORY, KYIV
    exclude_crimea = False   # independent toggle (still useful if area=ALL)

    out_dir = OUT_DIR

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
        area=area,   # <--- NEW
    )

    os.makedirs(out_dir, exist_ok=True)

    suffix = area.lower()
    out_csv = os.path.join(out_dir, f"ua_trends_{category}_{language}_{suffix}_yearly_avg.csv")
    out_png = os.path.join(out_dir, f"ua_trends_{category}_{language}_{suffix}_yearly_avg.png")

    df_year.to_csv(out_csv, index=False, encoding="utf-8-sig")

    lang_label = "Ukrainian term score" if language == "ua" else "Russian term score"
    title = f"Ukraine Google Trends — {area} avg by year ({lang_label})"
    if exclude_crimea:
        title += " [excluding Crimea/Sevastopol]"

    plot_country_barchart(df_year, language, title, out_png)

    print(f"Saved:\n  {out_csv}\n  {out_png}")




if __name__ == "__main__":
    main()
















