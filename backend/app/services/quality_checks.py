"""
The data quality engine.

This is the logic from your Streamlit app.py, moved into a plain Python module
with NO Streamlit code inside. Every function takes a DataFrame and returns
plain data, so the API (and the tests) can use it.
"""
import re

import numpy as np
import pandas as pd

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# The standard onboarding statuses the checker expects (same list as the original app).
STANDARD_STATUS_LABELS = {
    "not started": "Not Started",
    "pending": "Pending",
    "in progress": "In Progress",
    "blocked": "Blocked",
    "waiting on customer": "Waiting on Customer",
    "on hold": "On Hold",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

# Column names containing these words are treated as that kind of column.
EMAIL_KEYWORDS = ["email", "e-mail"]
PHONE_KEYWORDS = ["phone", "mobile", "telephone", "contact"]
DATE_KEYWORDS = ["date", "dob", "birth", "created", "updated", "joined"]

MAX_VALUE_LENGTH = 200


# ---------------------------------------------------------------- small helpers

def find_columns(df, keywords):
    """Find columns whose names contain one of the keywords."""
    return [c for c in df.columns if any(k in str(c).lower() for k in keywords)]


def get_blank_mask(series):
    """True where a cell is missing or only spaces."""
    return series.fillna("").astype(str).str.strip().eq("")


def normalize_text(value):
    """Trim, lowercase and collapse spaces so values are easy to compare."""
    return " ".join(str(value).strip().lower().split())


def resolve_columns(df, rules):
    """
    Decide which columns are email / phone / date / id / status.
    By default we guess from column names (like the original app).
    The user can override any of these with `rules` when uploading.
    """
    rules = rules or {}

    def pick(key, keywords):
        if key in rules and rules[key] is not None:
            return [c for c in rules[key] if c in df.columns]
        return find_columns(df, keywords)

    def pick_one(key, default):
        value = rules[key] if key in rules else default
        return value if value in df.columns else None

    return {
        "email_columns": pick("email_columns", EMAIL_KEYWORDS),
        "phone_columns": pick("phone_columns", PHONE_KEYWORDS),
        "date_columns": pick("date_columns", DATE_KEYWORDS),
        "id_column": pick_one("id_column", "customer_id"),
        "status_column": pick_one("status_column", "onboarding_status"),
    }


# ---------------------------------------------------------------- individual checks

def check_email_values(df, email_columns):
    results, masks = {}, {}
    for column in email_columns:
        values = df[column].fillna("").astype(str).str.strip()
        missing = get_blank_mask(df[column])
        invalid = (~missing) & (~values.str.match(EMAIL_PATTERN))
        results[column] = int(invalid.sum())
        masks[column] = invalid
    return results, masks


def check_phone_values(df, phone_columns):
    """A valid phone has 7 to 15 digits once separators are removed."""
    results, masks = {}, {}
    for column in phone_columns:
        values = df[column].fillna("").astype(str).str.strip()
        missing = get_blank_mask(df[column])
        digit_counts = values.str.replace(r"\D", "", regex=True).str.len()
        invalid = (~missing) & ((digit_counts < 7) | (digit_counts > 15))
        results[column] = int(invalid.sum())
        masks[column] = invalid
    return results, masks


def check_date_values(df, date_columns):
    results = {}
    for column in date_columns:
        raw = df[column]
        missing = get_blank_mask(raw)
        parsed = pd.to_datetime(raw.where(~missing), errors="coerce")
        invalid = parsed.isna() & (~missing)
        results[column] = {
            "missing": int(missing.sum()),
            "invalid": int(invalid.sum()),
            "parsed_dates": parsed,
            "missing_mask": missing,
            "invalid_mask": invalid,
        }
    return results


def check_status_values(df, status_column):
    empty = {
        "missing": 0, "label_mismatch": 0, "non_standard": 0,
        "table": [], "distribution": [],
        "missing_mask": pd.Series(False, index=df.index),
        "bad_mask": pd.Series(False, index=df.index),
    }
    if status_column is None:
        return empty

    status_values = df[status_column].fillna("").astype(str).str.strip()
    missing_mask = status_values.eq("")
    normalized = status_values.map(normalize_text)

    expected = normalized.map(STANDARD_STATUS_LABELS)
    known = expected.notna()
    label_mismatch = known & (status_values != expected)
    non_standard = (~missing_mask) & (~known)

    table = pd.DataFrame({
        "current_value": status_values,
        "recommended_value": expected.fillna("Needs review"),
        "rows": status_values.map(status_values.value_counts()),
        "issue_type": "Looks good",
    })
    table.loc[label_mismatch, "issue_type"] = "Inconsistent label"
    table.loc[non_standard, "issue_type"] = "Non-standard value"
    table.loc[missing_mask, "issue_type"] = "Missing value"
    table = table.drop_duplicates().sort_values(["issue_type", "current_value"])

    distribution = (
        status_values.replace("", "(blank)").value_counts().head(15)
        .rename_axis("status").reset_index(name="count")
    )

    return {
        "missing": int(missing_mask.sum()),
        "label_mismatch": int(label_mismatch.sum()),
        "non_standard": int(non_standard.sum()),
        "table": table.to_dict(orient="records"),
        "distribution": distribution.to_dict(orient="records"),
        "missing_mask": missing_mask,
        "bad_mask": label_mismatch | non_standard,
    }


# ---------------------------------------------------------------- score + advice

def calculate_quality_score(total_rows, total_columns, issue_count):
    """Fewer issues compared to the number of cells = higher score (0 to 100)."""
    total_cells = max(total_rows * total_columns, 1)
    issue_rate = min(issue_count / total_cells, 1)
    return round((1 - issue_rate) * 100, 1)


def score_label(score):
    if score >= 95:
        return "Launch ready"
    if score >= 85:
        return "Needs light cleanup"
    if score >= 70:
        return "Needs focused cleanup"
    return "Migration risk"


def build_recommendations(missing_by_column, duplicate_rows, duplicate_id_count,
                          invalid_emails, invalid_phones, date_results, status_issue_count):
    """Plain-English advice, same wording as the original dashboard."""
    recs = []

    with_missing = missing_by_column[missing_by_column > 0]
    if not with_missing.empty:
        recs.append({"priority": "High", "title": "Complete required fields",
                     "detail": f"Review missing values in: {', '.join(map(str, with_missing.index))}."})

    if duplicate_rows > 0 or duplicate_id_count > 0:
        recs.append({"priority": "High", "title": "Resolve duplicate customer records",
                     "detail": "Deduplicate exact rows and duplicate customer IDs before migration."})

    for column, count in invalid_emails.items():
        if count > 0:
            recs.append({"priority": "Medium", "title": "Repair email addresses",
                         "detail": f"Standardize or correct {count} invalid email values in {column}."})

    for column, count in invalid_phones.items():
        if count > 0:
            recs.append({"priority": "Medium", "title": "Standardize phone numbers",
                         "detail": f"Clean {count} phone values in {column} to a consistent format."})

    for column, result in date_results.items():
        if result["missing"] > 0 or result["invalid"] > 0:
            recs.append({"priority": "Medium", "title": "Normalize date fields",
                         "detail": f"Fix missing or invalid date values in {column}."})

    if status_issue_count > 0:
        recs.append({"priority": "Low", "title": "Create a status dictionary",
                     "detail": "Map onboarding status values to one approved list before operational reporting."})

    if not recs:
        recs.append({"priority": "Low", "title": "Data looks ready",
                     "detail": "No major data quality issues were found. This dataset is ready for analysis."})
    return recs


# ---------------------------------------------------------------- row-level issues

def _cell_text(df, position, column):
    value = df[column].iloc[position]
    return "" if pd.isna(value) else str(value)[:MAX_VALUE_LENGTH]


def _collect_issues(df, masks_by_type, limit):
    """
    Turn boolean masks into a flat list of issues:
    [{row_number, column_name, issue_type, value}, ...]
    Row numbers match a spreadsheet (header is row 1, first data row is 2).
    Returns (issues, was_truncated).
    """
    issues, truncated = [], False
    for issue_type, column, mask in masks_by_type:
        for position in np.flatnonzero(mask.to_numpy()):
            if len(issues) >= limit:
                return issues, True
            issues.append({
                "row_number": int(position) + 2,
                "column_name": str(column),
                "issue_type": issue_type,
                "value": "" if column == "(whole row)" else _cell_text(df, position, column),
            })
    return issues, truncated


# ---------------------------------------------------------------- the main entry point

def analyze(df, rules=None, issue_limit=20000):
    """
    Run every check on a DataFrame.
    Returns (report, issues):
      report -> a JSON-friendly dict with scores, charts data, details, advice
      issues -> a list of row-level problems (for the "problem rows" table)
    """
    cols = resolve_columns(df, rules)
    total_rows, total_columns = len(df), len(df.columns)

    # Duplicates
    duplicate_rows = int(df.duplicated().sum())
    duplicate_row_mask = df.duplicated(keep=False)
    id_column = cols["id_column"]
    if id_column:
        duplicate_id_count = int(df[id_column].duplicated().sum())
        duplicate_id_mask = df[id_column].duplicated(keep=False)
    else:
        duplicate_id_count = 0
        duplicate_id_mask = pd.Series(False, index=df.index)

    # Missing values
    missing_by_cell = df.apply(get_blank_mask)
    missing_by_column = missing_by_cell.sum()
    missing_values = int(missing_by_column.sum())

    # Format checks
    invalid_emails, email_masks = check_email_values(df, cols["email_columns"])
    invalid_phones, phone_masks = check_phone_values(df, cols["phone_columns"])
    date_results = check_date_values(df, cols["date_columns"])
    status = check_status_values(df, cols["status_column"])

    invalid_email_count = sum(invalid_emails.values())
    invalid_phone_count = sum(invalid_phones.values())
    invalid_date_count = sum(r["missing"] + r["invalid"] for r in date_results.values())
    status_issue_count = status["missing"] + status["label_mismatch"] + status["non_standard"]

    issue_count = (missing_values + duplicate_rows + duplicate_id_count + invalid_email_count
                   + invalid_phone_count + invalid_date_count + status_issue_count)
    score = calculate_quality_score(total_rows, total_columns, issue_count)

    # Row-level issues (order here = order they are saved if we hit the limit)
    masks = []
    for column in df.columns:
        masks.append(("missing_value", column, missing_by_cell[column]))
    masks.append(("duplicate_row", "(whole row)", duplicate_row_mask))
    if id_column:
        masks.append(("duplicate_id", id_column, duplicate_id_mask))
    for column, mask in email_masks.items():
        masks.append(("invalid_email", column, mask))
    for column, mask in phone_masks.items():
        masks.append(("invalid_phone", column, mask))
    for column, result in date_results.items():
        masks.append(("invalid_date", column, result["invalid_mask"]))
    if cols["status_column"]:
        masks.append(("status_issue", cols["status_column"], status["bad_mask"]))
    issues, truncated = _collect_issues(df, masks, issue_limit)

    # Records over time for the first date column that has valid dates
    date_trend = None
    for column, result in date_results.items():
        parsed = result["parsed_dates"].dropna()
        if not parsed.empty:
            monthly = parsed.dt.to_period("M").astype(str).value_counts().sort_index()
            date_trend = {"column": str(column),
                          "points": [{"month": m, "count": int(n)} for m, n in monthly.items()]}
            break

    report = {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "quality_score": score,
        "score_label": score_label(score),
        "issue_count": issue_count,
        "duplicate_rows": duplicate_rows,
        "duplicate_ids": duplicate_id_count,
        "missing_values": missing_values,
        "issue_summary": [
            {"issue": "Missing values", "count": missing_values},
            {"issue": "Duplicate rows", "count": duplicate_rows},
            {"issue": "Duplicate IDs", "count": duplicate_id_count},
            {"issue": "Invalid emails", "count": invalid_email_count},
            {"issue": "Invalid phones", "count": invalid_phone_count},
            {"issue": "Date issues", "count": invalid_date_count},
            {"issue": "Status issues", "count": status_issue_count},
        ],
        "missing_by_column": [{"column": str(c), "count": int(n)} for c, n in missing_by_column.items()],
        "invalid_emails": {str(k): v for k, v in invalid_emails.items()},
        "invalid_phones": {str(k): v for k, v in invalid_phones.items()},
        "dates": {str(c): {"missing": r["missing"], "invalid": r["invalid"]} for c, r in date_results.items()},
        "status": {
            "column": cols["status_column"],
            "missing": status["missing"],
            "label_mismatch": status["label_mismatch"],
            "non_standard": status["non_standard"],
            "table": status["table"],
            "distribution": status["distribution"],
        },
        "date_trend": date_trend,
        "detected_columns": {k: v for k, v in cols.items()},
        "rules": rules or {},
        "recommendations": build_recommendations(
            missing_by_column, duplicate_rows, duplicate_id_count,
            invalid_emails, invalid_phones, date_results, status_issue_count),
        "issues_truncated": truncated,
    }
    return report, issues
