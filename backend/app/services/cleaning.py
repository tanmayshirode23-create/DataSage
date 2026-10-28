"""Build a cleaned copy of a dataset (for the 'Download cleaned CSV' button)."""
import pandas as pd

from .quality_checks import STANDARD_STATUS_LABELS, get_blank_mask, normalize_text, resolve_columns


def clean_dataframe(df, rules=None):
    """
    Safe, automatic fixes only:
      1. trim spaces around text
      2. lowercase emails
      3. write dates as YYYY-MM-DD (unreadable dates become blank)
      4. use the standard spelling for known statuses
      5. remove exact duplicate rows, then repeated IDs (keeps the first)
    Anything that needs a human decision (bad phones, blanks) is left untouched.
    Returns (cleaned_df, stats).
    """
    cols = resolve_columns(df, rules)
    out = df.copy()
    rows_before = len(out)

    for column in out.columns:
        if pd.api.types.is_string_dtype(out[column]) or pd.api.types.is_object_dtype(out[column]):
            out[column] = out[column].map(lambda v: v.strip() if isinstance(v, str) else v)

    for column in cols["email_columns"]:
        out[column] = out[column].map(lambda v: v.lower() if isinstance(v, str) else v)

    dates_fixed = 0
    for column in cols["date_columns"]:
        blank = get_blank_mask(out[column])
        parsed = pd.to_datetime(out[column].where(~blank), errors="coerce")
        formatted = parsed.dt.strftime("%Y-%m-%d")
        dates_fixed += int((formatted.notna() & (formatted != out[column].astype(str))).sum())
        out[column] = formatted

    statuses_fixed = 0
    status_column = cols["status_column"]
    if status_column:
        def standardize(value):
            if not isinstance(value, str):
                return value
            return STANDARD_STATUS_LABELS.get(normalize_text(value), value)
        standardized = out[status_column].map(standardize)
        statuses_fixed = int((standardized != out[status_column]).fillna(False).sum())
        out[status_column] = standardized

    out = out.drop_duplicates()
    after_exact = len(out)

    id_column = cols["id_column"]
    if id_column:
        repeated_id = out[id_column].duplicated() & ~get_blank_mask(out[id_column])
        out = out[~repeated_id]

    stats = {
        "rows_before": rows_before,
        "rows_after": len(out),
        "duplicate_rows_removed": rows_before - after_exact,
        "duplicate_ids_removed": after_exact - len(out),
        "dates_standardized": dates_fixed,
        "statuses_standardized": statuses_fixed,
    }
    return out, stats
