"""
Compare World Cup results with staff predictions.

Output:
    correct_winner_predictions.csv

The output contains only predictions where the person correctly
identified the country that advanced. It also indicates whether
the exact score was predicted correctly.

Required packages:
    pandas
    openpyxl
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
import unicodedata

import pandas as pd


# ---------------------------------------------------------------------
# FILE SETTINGS
# ---------------------------------------------------------------------

RESULTS_FILE = Path(
    r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work"
    r"\GIS_SPECIALIST\World_Cup_Pool\fifa-world-cup-2026-UTC.csv"
)

PREDICTIONS_FILE = Path(
    r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work"
    r"\GIS_SPECIALIST\World_Cup_Pool\World Cup 2026 Pool - results.csv"
)



OUTPUT_CSV = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\World_Cup_Pool\correct_winner_predictions.csv")
ISSUES_CSV = Path(r"\\spatialfiles.bcgov\srm\wml\Workarea\ofedyshy\Other Work\GIS_SPECIALIST\World_Cup_Pool\unmatched_predictions.csv")


# ---------------------------------------------------------------------
# GENERAL CLEANING FUNCTIONS
# ---------------------------------------------------------------------

def clean_header(value: object) -> str:
    """Convert a column heading into a simple comparable string."""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
    required: bool = True,
) -> str | None:
    """
    Find a column using flexible heading matching.

    For example:
        'Round Number' matches 'roundnumber'
        'Who will advance?' matches 'whowilladvance'
    """
    normalized_columns = {
        clean_header(column): column
        for column in dataframe.columns
    }

    # First try exact normalized matches.
    for candidate in candidates:
        normalized_candidate = clean_header(candidate)

        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]

    # Then try partial matches.
    for candidate in candidates:
        normalized_candidate = clean_header(candidate)

        for normalized_column, original_column in normalized_columns.items():
            if normalized_candidate in normalized_column:
                return original_column

    if required:
        raise KeyError(
            f"Could not find a column matching any of these names: "
            f"{candidates}\n\nAvailable columns:\n"
            f"{list(dataframe.columns)}"
        )

    return None


def remove_accents(value: str) -> str:
    """Remove accents and other diacritical marks."""
    normalized = unicodedata.normalize("NFKD", value)

    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


# ---------------------------------------------------------------------
# TEAM-NAME CLEANING
# ---------------------------------------------------------------------

TEAM_ALIASES = {
    "usa": "unitedstates",
    "us": "unitedstates",
    "unitedstatesofamerica": "unitedstates",

    "congodr": "drcongo",
    "democraticrepublicofthecongo": "drcongo",

    "caboverde": "capeverde",

    "cotedivoire": "ivorycoast",

    "korearepublic": "southkorea",
    "republicofkorea": "southkorea",

    "czechrepublic": "czechia",

    "turkiye": "turkey",
}


def normalize_team(value: object) -> str:
    """Return a standardized team key for matching."""
    if pd.isna(value):
        return ""

    text = remove_accents(str(value)).lower().strip()
    key = re.sub(r"[^a-z0-9]+", "", text)

    return TEAM_ALIASES.get(key, key)


# ---------------------------------------------------------------------
# STAGE CLEANING
# ---------------------------------------------------------------------

STAGE_ALIASES = {
    "roundof32": "round_of_32",
    "round32": "round_of_32",
    "r32": "round_of_32",

    "roundof16": "round_of_16",
    "round16": "round_of_16",
    "r16": "round_of_16",

    "quarterfinal": "quarterfinal",
    "quarterfinals": "quarterfinal",
    "qf": "quarterfinal",

    "semifinal": "semifinal",
    "semifinals": "semifinal",
    "sf": "semifinal",

    "final": "final",
    "finals": "final",
}


NEXT_STAGE = {
    "round_of_32": "round_of_16",
    "round_of_16": "quarterfinal",
    "quarterfinal": "semifinal",
    "semifinal": "final",
}


def normalize_stage(value: object) -> str:
    """Standardize stage names between the two workbooks."""
    if pd.isna(value):
        return ""

    key = re.sub(r"[^a-z0-9]+", "", str(value).lower())

    return STAGE_ALIASES.get(key, key)


# ---------------------------------------------------------------------
# SCORE CLEANING
# ---------------------------------------------------------------------

def parse_score(value: object) -> tuple[int, int] | None:
    """
    Convert a score into a home-score, away-score tuple.

    Examples:
        '2 - 1'  -> (2, 1)
        '2-1'    -> (2, 1)
        '01-Feb' -> (2, 1)

    For Excel dates, month is treated as the home-team score and
    day is treated as the away-team score.
    """
    if pd.isna(value):
        return None

    # Pandas may import an Excel-formatted score as a date.
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return int(value.month), int(value.day)

    text = str(value).strip()

    if not text:
        return None

    # Detect date-like text before looking for a score.
    # This prevents a full date such as 1900-02-01 from becoming 1900-02.
    contains_month_name = bool(re.search(r"[A-Za-z]", text))
    contains_four_digit_year = bool(re.search(r"\b\d{4}\b", text))

    if contains_month_name or contains_four_digit_year:
        parsed_date = pd.to_datetime(text, errors="coerce")

        if not pd.isna(parsed_date):
            return int(parsed_date.month), int(parsed_date.day)

    # Ordinary score formats: 2-1, 2 - 1, 2:1, or 2–1.
    score_match = re.search(
        r"(?<!\d)(\d{1,2})\s*[-–—:]\s*(\d{1,2})(?!\d)",
        text,
    )

    if score_match:
        return int(score_match.group(1)), int(score_match.group(2))

    return None


def format_score(score: tuple[int, int] | None) -> str:
    """Convert a score tuple back into readable text."""
    if score is None:
        return ""

    return f"{score[0]}-{score[1]}"


def format_date(value: object) -> str:
    """Create a readable date for the output CSV."""
    if pd.isna(value):
        return ""

    parsed = pd.to_datetime(value, errors="coerce")

    if not pd.isna(parsed):
        return parsed.strftime("%Y-%m-%d")

    return str(value)


# ---------------------------------------------------------------------
# READ THE WORKBOOKS
# ---------------------------------------------------------------------

results = pd.read_csv(
    RESULTS_FILE,
    encoding="utf-8-sig",
)

predictions = pd.read_csv(
    PREDICTIONS_FILE,
    encoding="utf-8-sig",
)


# ---------------------------------------------------------------------
# IDENTIFY RESULTS COLUMNS
# ---------------------------------------------------------------------

results_match_column = find_column(
    results,
    ["Match Number", "Match"],
)

results_stage_column = find_column(
    results,
    ["Round Number", "Round", "Stage"],
)

results_home_column = find_column(
    results,
    ["Home Team", "Home"],
)

results_away_column = find_column(
    results,
    ["Away Team", "Away"],
)

results_score_column = find_column(
    results,
    ["Result", "Score", "Final Score"],
)

results_date_column = find_column(
    results,
    ["Date", "Match Date"],
    required=False,
)

# Optional. This is helpful for matches decided by penalties.
results_winner_column = find_column(
    results,
    ["Winner", "Advancing Team", "Team Advancing"],
    required=False,
)


# ---------------------------------------------------------------------
# IDENTIFY PREDICTION COLUMNS
# ---------------------------------------------------------------------

prediction_id_column = find_column(
    predictions,
    ["ID"],
    required=False,
)

prediction_name_column = find_column(
    predictions,
    ["Name"],
    required=False,
)

prediction_email_column = find_column(
    predictions,
    ["Email"],
    required=False,
)

prediction_stage_column = find_column(
    predictions,
    ["Stage", "Round"],
)

prediction_winner_column = find_column(
    predictions,
    ["Who will advance", "Who will win", "Predicted Winner"],
)

prediction_score_column = find_column(
    predictions,
    ["Final score", "Predicted Score", "Score"],
)

prediction_pool_column = find_column(
    predictions,
    [
        "Pick your South Area",
        "South Area Team",
        "Pool Team",
    ],
    required=False,
)


# ---------------------------------------------------------------------
# PREPARE RESULTS
# ---------------------------------------------------------------------

results = results.copy()

results["_stage_key"] = results[results_stage_column].apply(normalize_stage)
results["_home_key"] = results[results_home_column].apply(normalize_team)
results["_away_key"] = results[results_away_column].apply(normalize_team)
results["_score_tuple"] = results[results_score_column].apply(parse_score)

results["_winner_key"] = ""
results["_winner_display"] = ""


# First use an explicit Winner column, when one exists.
if results_winner_column:
    for index, row in results.iterrows():
        explicit_winner = normalize_team(row[results_winner_column])

        if explicit_winner in {
            row["_home_key"],
            row["_away_key"],
        }:
            results.at[index, "_winner_key"] = explicit_winner
            results.at[index, "_winner_display"] = (
                row[results_home_column]
                if explicit_winner == row["_home_key"]
                else row[results_away_column]
            )


# Derive winners from non-tied scores.
for index, row in results.iterrows():
    if row["_winner_key"]:
        continue

    score = row["_score_tuple"]

    if score is None:
        continue

    home_score, away_score = score

    if home_score > away_score:
        results.at[index, "_winner_key"] = row["_home_key"]
        results.at[index, "_winner_display"] = row[results_home_column]

    elif away_score > home_score:
        results.at[index, "_winner_key"] = row["_away_key"]
        results.at[index, "_winner_display"] = row[results_away_column]


# For tied knockout scores, infer the winner by checking which team
# appears in the following round.
for index, row in results.iterrows():
    if row["_winner_key"]:
        continue

    next_stage = NEXT_STAGE.get(row["_stage_key"])

    if not next_stage:
        continue

    following_round = results[
        results["_stage_key"] == next_stage
    ]

    following_teams = set(following_round["_home_key"]).union(
        set(following_round["_away_key"])
    )

    possible_winners = [
        team
        for team in [row["_home_key"], row["_away_key"]]
        if team in following_teams
    ]

    if len(possible_winners) == 1:
        inferred_winner = possible_winners[0]

        results.at[index, "_winner_key"] = inferred_winner
        results.at[index, "_winner_display"] = (
            row[results_home_column]
            if inferred_winner == row["_home_key"]
            else row[results_away_column]
        )


# ---------------------------------------------------------------------
# COMPARE THE PREDICTIONS
# ---------------------------------------------------------------------

correct_predictions: list[dict[str, object]] = []
prediction_issues: list[dict[str, object]] = []

for prediction_index, prediction in predictions.iterrows():
    predicted_stage = normalize_stage(
        prediction[prediction_stage_column]
    )

    predicted_winner_key = normalize_team(
        prediction[prediction_winner_column]
    )

    if not predicted_stage or not predicted_winner_key:
        continue

    # A team appears only once in a particular knockout stage,
    # so stage + selected team identifies the relevant match.
    matching_games = results[
        (results["_stage_key"] == predicted_stage)
        & (
            (results["_home_key"] == predicted_winner_key)
            | (results["_away_key"] == predicted_winner_key)
        )
    ]

    if len(matching_games) == 0:
        prediction_issues.append(
            {
                "Prediction row": prediction_index + 2,
                "Name": (
                    prediction[prediction_name_column]
                    if prediction_name_column
                    else ""
                ),
                "Stage": prediction[prediction_stage_column],
                "Predicted winner": prediction[prediction_winner_column],
                "Issue": "No matching game found",
            }
        )
        continue

    if len(matching_games) > 1:
        prediction_issues.append(
            {
                "Prediction row": prediction_index + 2,
                "Name": (
                    prediction[prediction_name_column]
                    if prediction_name_column
                    else ""
                ),
                "Stage": prediction[prediction_stage_column],
                "Predicted winner": prediction[prediction_winner_column],
                "Issue": "More than one matching game found",
            }
        )
        continue

    game = matching_games.iloc[0]

    if not game["_winner_key"]:
        prediction_issues.append(
            {
                "Prediction row": prediction_index + 2,
                "Name": (
                    prediction[prediction_name_column]
                    if prediction_name_column
                    else ""
                ),
                "Stage": prediction[prediction_stage_column],
                "Predicted winner": prediction[prediction_winner_column],
                "Issue": (
                    "The actual winner could not be determined. "
                    "Add a Winner column to the results workbook."
                ),
            }
        )
        continue

    # Keep only people who selected the actual winner.
    if predicted_winner_key != game["_winner_key"]:
        continue

    predicted_score = parse_score(
        prediction[prediction_score_column]
    )

    actual_score = game["_score_tuple"]

    exact_score = (
        predicted_score is not None
        and actual_score is not None
        and predicted_score == actual_score
    )

    output_record = {
        "Prediction ID": (
            prediction[prediction_id_column]
            if prediction_id_column
            else ""
        ),
        "Name": (
            prediction[prediction_name_column]
            if prediction_name_column
            else ""
        ),
        "Email": (
            prediction[prediction_email_column]
            if prediction_email_column
            else ""
        ),
        "Pool Team": (
            prediction[prediction_pool_column]
            if prediction_pool_column
            else ""
        ),
        "Stage": game[results_stage_column],
        "Match Number": game[results_match_column],
        "Match Date": (
            format_date(game[results_date_column])
            if results_date_column
            else ""
        ),
        "Home Team": game[results_home_column],
        "Away Team": game[results_away_column],
        "Predicted Winner": prediction[prediction_winner_column],
        "Actual Winner": game["_winner_display"],
        "Predicted Score": format_score(predicted_score),
        "Actual Score": format_score(actual_score),
        "Exact Score": "Yes" if exact_score else "No",
    }

    correct_predictions.append(output_record)


# ---------------------------------------------------------------------
# EXPORT THE RESULTS
# ---------------------------------------------------------------------

correct_dataframe = pd.DataFrame(correct_predictions)

if not correct_dataframe.empty:
    correct_dataframe = correct_dataframe.sort_values(
        by=["Match Number", "Name"],
        na_position="last",
    )

correct_dataframe.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig",
)

print(
    f"Created {OUTPUT_CSV}\n"
    f"Correct winner predictions: {len(correct_dataframe)}"
)


# Create a separate troubleshooting file only when necessary.
if prediction_issues:
    issues_dataframe = pd.DataFrame(prediction_issues)

    issues_dataframe.to_csv(
        ISSUES_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"\nSome predictions could not be matched.\n"
        f"Review: {ISSUES_CSV}"
    )