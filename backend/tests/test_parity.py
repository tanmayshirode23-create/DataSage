"""
Proves the new engine gives the SAME numbers as the original Streamlit app.
We import the original app.py (with Streamlit replaced by a dummy) and
compare its results with services/quality_checks.py on the sample CSV.
"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "backend" / "sample_data" / "sample_customer_data.csv"


@pytest.fixture(scope="module")
def legacy():
    sys.modules["streamlit"] = MagicMock()
    spec = importlib.util.spec_from_file_location("legacy_app", ROOT / "legacy_streamlit" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacy_numbers(m, df):
    """Repeat the counting steps from the original main()."""
    missing_by_cell = df.apply(m.get_blank_mask)
    missing_values = int(missing_by_cell.sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    duplicate_ids = int(df["customer_id"].duplicated().sum())
    emails, _ = m.check_email_values(df, m.find_columns(df, ["email", "e-mail"]))
    phones, _ = m.check_phone_values(df, m.find_columns(df, ["phone", "mobile", "telephone", "contact"]))
    dates = m.check_date_values(df, m.find_columns(df, ["date", "dob", "birth", "created", "updated", "joined"]))
    status = m.check_status_values(df)
    date_issues = sum(r["missing"] + r["invalid"] for r in dates.values())
    status_issues = status["missing"] + status["label_mismatch"] + status["non_standard"]
    total = (missing_values + duplicate_rows + duplicate_ids + sum(emails.values())
             + sum(phones.values()) + date_issues + status_issues)
    return {
        "missing_values": missing_values, "duplicate_rows": duplicate_rows, "duplicate_ids": duplicate_ids,
        "emails": sum(emails.values()), "phones": sum(phones.values()),
        "dates": date_issues, "status": status_issues, "issue_count": total,
        "score": m.calculate_quality_score(len(df), len(df.columns), total),
        "label": m.score_label(m.calculate_quality_score(len(df), len(df.columns), total)),
    }


def test_engine_matches_original_streamlit_app(legacy):
    from app.services.quality_checks import analyze

    df = pd.read_csv(SAMPLE)
    expected = legacy_numbers(legacy, df)
    report, issues = analyze(df)
    summary = {row["issue"]: row["count"] for row in report["issue_summary"]}

    assert summary["Missing values"] == expected["missing_values"]
    assert summary["Duplicate rows"] == expected["duplicate_rows"]
    assert summary["Duplicate IDs"] == expected["duplicate_ids"]
    assert summary["Invalid emails"] == expected["emails"]
    assert summary["Invalid phones"] == expected["phones"]
    assert summary["Date issues"] == expected["dates"]
    assert summary["Status issues"] == expected["status"]
    assert report["issue_count"] == expected["issue_count"]
    assert report["quality_score"] == expected["score"]
    assert report["score_label"] == expected["label"]
    print("\nORIGINAL vs NEW:", expected["score"], report["quality_score"], expected["label"])


def test_recommendations_match_original(legacy):
    from app.services.quality_checks import analyze

    df = pd.read_csv(SAMPLE)
    m = legacy
    missing_by_column = df.apply(m.get_blank_mask).sum()
    emails, _ = m.check_email_values(df, m.find_columns(df, ["email", "e-mail"]))
    phones, _ = m.check_phone_values(df, m.find_columns(df, ["phone", "mobile", "telephone", "contact"]))
    dates = m.check_date_values(df, m.find_columns(df, ["date", "dob", "birth", "created", "updated", "joined"]))
    status = m.check_status_values(df)
    old = m.build_recommendations(missing_by_column, int(df.duplicated().sum()),
                                  int(df["customer_id"].duplicated().sum()), emails, phones, dates, status)
    new = analyze(df)[0]["recommendations"]
    assert new == old
