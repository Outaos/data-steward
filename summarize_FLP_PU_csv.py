from pathlib import Path
import pandas as pd


def main():
    # ------------------------------------------------------------------
    # USER SETTINGS
    # ------------------------------------------------------------------
    input_csv = Path(r"\\spatialfiles.bcgov\Work\for\RSI\SA\Tasks\2026\3394\Incoming\Beaver.csv")
    output_folder = input_csv.parent / f"{input_csv.stem}_summaries"

    # Fields retained so summaries remain separate for each planning unit.
    id_fields = ["aoi", "UnitName"]

    sum_fields = [
        "ogmaPERM_ha",
        "ogmaROT_ha",
        "ogmaTRANS_ha",
        "TAP_ha",
        "loggedHistory_ha",
        "fireHistory_ha",
        "mpbHistory_ha",
        "rec_ha",
        "roads_ha",
        "hydro_ha",
        "Area_ha",
    ]

    # Desired row order in each summary.
    summary_fields = {
        "landbase": ["THLB", "nonAFLB", "nonTHLB"],
        "hsys": ["evenAge", "grass", "unevenAge"],
        "seralStage": [
            "<10yrs",
            "10-20yrs",
            "21-40yrs",
            "41-80yrs",
            "81-250yrs",
            ">250yrs",
        ],
    }

    decimal_places = 6

    # ------------------------------------------------------------------
    # READ AND VALIDATE INPUT
    # ------------------------------------------------------------------
    df = pd.read_csv(input_csv)

    required_fields = id_fields + list(summary_fields) + sum_fields
    missing_fields = [field for field in required_fields if field not in df.columns]

    if missing_fields:
        raise ValueError(
            "The input CSV is missing these required fields: "
            + ", ".join(missing_fields)
        )

    # Convert area fields to numeric. Blank or invalid values become zero.
    for field in sum_fields:
        df[field] = pd.to_numeric(df[field], errors="coerce").fillna(0)

    output_folder.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # CREATE ONE SUMMARY CSV FOR EACH CLASSIFICATION FIELD
    # ------------------------------------------------------------------
    for group_field, category_order in summary_fields.items():
        group_fields = id_fields + [group_field]

        summary = (
            df.groupby(group_fields, dropna=False, as_index=False)[sum_fields]
            .sum()
        )

        # Apply the requested category order.
        summary[group_field] = pd.Categorical(
            summary[group_field],
            categories=category_order,
            ordered=True,
        )

        summary = (
            summary.sort_values(id_fields + [group_field])
            .reset_index(drop=True)
        )

        # Convert the categorical field back to normal text before export.
        summary[group_field] = summary[group_field].astype("object")
        summary[sum_fields] = summary[sum_fields].round(decimal_places)

        output_csv = output_folder / f"summary_by_{group_field}.csv"
        summary.to_csv(output_csv, index=False, encoding="utf-8-sig")

        print(f"Created: {output_csv}")

    print("\nDone.")


if __name__ == "__main__":
    main()