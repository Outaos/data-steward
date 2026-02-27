"""
Download Google Trends yearly "interest by subregion" for Ukraine (UA)
for Ukrainian vs Russian spelling word pairs, 2011–2025 inclusive.

1) Install:
   pip install pytrends pandas

2) Run:
   python ua_trends_by_region_year.py

Output:
- ua_trends_by_region_year_2011_2025.csv

NOTES / CAVEATS:
- Google Trends values are normalized 0–100 *within each request* (keyword set + geo + timeframe).
- Subregions returned by Google may vary by year and may exclude/rename some regions.
- Data is sampled; repeated runs can differ slightly.
- Be gentle with rate limits (script sleeps and retries).
"""

from __future__ import annotations

import time
import random
import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import pandas as pd
from pytrends.request import TrendReq


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
COUNTRY_GEO = "UA"
START_YEAR = 2011
END_YEAR = 2025

# Word pairs from your screenshot (Ukrainian Cyrillic, Russian Cyrillic)
WORD_PAIRS = [


    ("різати", "резать"),
    ("солити", "солить"),
    ("перчити", "перчить"),
    ("мішати", "мешать"),
    ("вареники", "пельмени"),
    ("млинці", "блины"),
    ("пиріг", "пирог"),
    ("печиво", "печенье"),



]




category = 'Food_5'

# pytrends locale/timezone (timezone in minutes; 0 is fine for normalized Trends)
HL = "uk-UA"
TZ = 0

# Rate limiting / retry behavior
SLEEP_BETWEEN_REQUESTS_SEC = (1.0, 2.0)  # original   (1.0, 2.0) 
MAX_RETRIES = 3
REQUEST_COUNT = 0



@dataclass
class QueryResult:
    year: int
    pair_id: int
    ua_term: str
    ru_term: str
    region: str
    score_ua: Optional[int]
    score_ru: Optional[int]


def _sleep_jitter(rng: tuple[float, float]) -> None:
    time.sleep(random.uniform(rng[0], rng[1]))


def _safe_interest_by_region(
    pytrends: TrendReq,
    kw_list: List[str],
    geo: str,
    timeframe: str,
    resolution: str = "REGION",
    inc_low_vol: bool = True,
    inc_geo_code: bool = False,
) -> pd.DataFrame:
    """
    Build payload + request interest_by_region with retries/backoff.
    Returns a DataFrame indexed by region with columns = keywords.
    """
    last_err: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            pytrends.build_payload(kw_list=kw_list, geo=geo, timeframe=timeframe)
            # micro-sleep to reduce "burstiness"
            time.sleep(random.uniform(1.5, 4.0))
            df = pytrends.interest_by_region(
                resolution=resolution,
                inc_low_vol=inc_low_vol,
                inc_geo_code=inc_geo_code,
            )
            global REQUEST_COUNT
            REQUEST_COUNT += 1

            # macro-sleep every 10 successful requests
            if REQUEST_COUNT % 10 == 0:
                time.sleep(random.uniform(60, 120))

            return df

        except Exception as e:
            last_err = e
            # Exponential backoff with jitter
            backoff = min(60, (2 ** attempt) + random.random() * 2)
            print(
                f"[WARN] Request failed (attempt {attempt}/{MAX_RETRIES}) "
                f"for kw={kw_list}, timeframe={timeframe}. "
                f"Backing off {backoff:.1f}s. Error: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            time.sleep(backoff)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries. Last error: {last_err}")


def main() -> None:
    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )

    pytrends = TrendReq(
        hl=HL,
        tz=TZ,
        timeout=(10, 30),
        requests_args={
            "headers": {"User-Agent": UA},
        },
    )


    results: List[Dict[str, Any]] = []

    pair_id = 0
    for ua_term, ru_term in WORD_PAIRS:
        pair_id += 1
        kw_list = [ua_term, ru_term]

        for year in range(START_YEAR, END_YEAR + 1):
            timeframe = f"{year}-01-01 {year}-12-31"
            #print(f"[INFO] Pair {pair_id}/{len(WORD_PAIRS)} | Year {year} | {kw_list}")

            df = _safe_interest_by_region(
                pytrends=pytrends,
                kw_list=kw_list,
                geo=COUNTRY_GEO,
                timeframe=timeframe,
                resolution="REGION",
                inc_low_vol=True,
                inc_geo_code=False,
            )

            # If Google returns nothing (rare), skip gracefully
            if df is None or df.empty:
                print(f"[WARN] Empty result for {kw_list} in {year}", file=sys.stderr)
                _sleep_jitter(SLEEP_BETWEEN_REQUESTS_SEC)
                continue

            # Ensure columns exist (sometimes one term can be missing due to low volume)
            if ua_term not in df.columns:
                df[ua_term] = pd.NA
            if ru_term not in df.columns:
                df[ru_term] = pd.NA

            # Convert to rows
            for region, row in df.iterrows():
                results.append(
                    {
                        "year": year,
                        "pair_id": pair_id,
                        "ua_term": ua_term,
                        "ru_term": ru_term,
                        "region": str(region),
                        "score_ua": None if pd.isna(row[ua_term]) else int(row[ua_term]),
                        "score_ru": None if pd.isna(row[ru_term]) else int(row[ru_term]),
                    }
                )

            _sleep_jitter(SLEEP_BETWEEN_REQUESTS_SEC)

    out = pd.DataFrame(results)

    # Helpful ordering
    if not out.empty:
        out = out.sort_values(["pair_id", "year", "region"]).reset_index(drop=True)

    #out_path = f"ua_trends_by_region_year_{START_YEAR}_{END_YEAR}.csv"
    

    OUTPUT_DIR = r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\ua_lang"
    

    # Ensure directory exists (safe even on network drive)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    out_path = os.path.join(
        OUTPUT_DIR,
        f"{category}_ua_trends_by_region_year_{START_YEAR}_{END_YEAR}.csv"
    )
    out.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\n[DONE] Wrote {len(out):,} rows to: {out_path}")
    print("Columns:", list(out.columns))


if __name__ == "__main__":
    main()
