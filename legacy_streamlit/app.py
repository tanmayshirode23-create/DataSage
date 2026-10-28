import html
import re
from pathlib import Path

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).parent
SAMPLE_FILE = APP_DIR / "data" / "sample_customer_data.csv"
SAMPLE_FILE_LABEL = "data/sample_customer_data.csv"

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# These are the standard onboarding statuses this dashboard expects.
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

CHART_PALETTE = [
    "#facc15",
    "#38bdf8",
    "#2563eb",
    "#fb7185",
    "#22c55e",
    "#a78bfa",
    "#f97316",
    "#14b8a6",
    "#e879f9",
    "#60a5fa",
    "#f59e0b",
    "#34d399",
]

ISSUE_COLORS = {
    "Missing values": "#facc15",
    "Duplicate rows": "#fb7185",
    "Duplicate IDs": "#f97316",
    "Invalid emails": "#38bdf8",
    "Invalid phones": "#2563eb",
    "Date issues": "#a78bfa",
    "Status issues": "#22c55e",
}


def load_data(uploaded_file):
    """Load the uploaded CSV, or use the included sample file."""
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file), uploaded_file.name

    return pd.read_csv(SAMPLE_FILE), SAMPLE_FILE_LABEL


def find_columns(df, keywords):
    """Find columns whose names contain one of the supplied keywords."""
    matching_columns = []

    for column in df.columns:
        column_name = column.lower()
        if any(keyword in column_name for keyword in keywords):
            matching_columns.append(column)

    return matching_columns


def get_blank_mask(series):
    """Treat blank strings and missing values as missing data."""
    return series.fillna("").astype(str).str.strip().eq("")


def normalize_text(value):
    """Make text easier to compare by trimming and collapsing spaces."""
    return " ".join(str(value).strip().lower().split())


def check_email_values(df, email_columns):
    """Return invalid email counts and row masks for each detected email column."""
    results = {}
    masks = {}

    for column in email_columns:
        values = df[column].fillna("").astype(str).str.strip()
        missing_mask = get_blank_mask(df[column])
        invalid_mask = (~missing_mask) & (~values.str.match(EMAIL_PATTERN))

        results[column] = int(invalid_mask.sum())
        masks[column] = invalid_mask

    return results, masks


def check_phone_values(df, phone_columns):
    """Return invalid phone counts and row masks for each detected phone column."""
    results = {}
    masks = {}

    for column in phone_columns:
        values = df[column].fillna("").astype(str).str.strip()
        missing_mask = get_blank_mask(df[column])

        # Keep the rule beginner-friendly: after removing common separators,
        # a valid phone number should contain 7 to 15 digits.
        digit_counts = values.str.replace(r"\D", "", regex=True).str.len()
        invalid_mask = (~missing_mask) & ((digit_counts < 7) | (digit_counts > 15))

        results[column] = int(invalid_mask.sum())
        masks[column] = invalid_mask

    return results, masks


def check_date_values(df, date_columns):
    """Return missing and invalid date counts, parsed dates, and row masks."""
    results = {}

    for column in date_columns:
        raw_values = df[column]
        missing_mask = get_blank_mask(raw_values)
        parsed_dates = pd.to_datetime(raw_values.where(~missing_mask), errors="coerce")
        invalid_mask = parsed_dates.isna() & (~missing_mask)

        results[column] = {
            "missing": int(missing_mask.sum()),
            "invalid": int(invalid_mask.sum()),
            "parsed_dates": parsed_dates,
            "missing_mask": missing_mask,
            "invalid_mask": invalid_mask,
        }

    return results


def check_status_values(df):
    """Detect inconsistent or non-standard onboarding status values."""
    if "onboarding_status" not in df.columns:
        return {
            "missing": 0,
            "label_mismatch": 0,
            "non_standard": 0,
            "table": pd.DataFrame(),
            "issue_mask": pd.Series(False, index=df.index),
        }

    status_values = df["onboarding_status"].fillna("").astype(str).str.strip()
    missing_mask = status_values.eq("")
    normalized = status_values.map(normalize_text)

    expected_labels = normalized.map(STANDARD_STATUS_LABELS)
    known_status_mask = expected_labels.notna()
    label_mismatch_mask = known_status_mask & (status_values != expected_labels)
    non_standard_mask = (~missing_mask) & (~known_status_mask)
    issue_mask = missing_mask | label_mismatch_mask | non_standard_mask

    status_table = pd.DataFrame(
        {
            "Current Value": status_values,
            "Recommended Value": expected_labels.fillna("Needs review"),
            "Rows": status_values.map(status_values.value_counts()),
            "Issue Type": "Looks good",
        }
    )
    status_table.loc[label_mismatch_mask, "Issue Type"] = "Inconsistent label"
    status_table.loc[non_standard_mask, "Issue Type"] = "Non-standard value"
    status_table.loc[missing_mask, "Issue Type"] = "Missing value"
    status_table = status_table.drop_duplicates().sort_values(["Issue Type", "Current Value"])

    return {
        "missing": int(missing_mask.sum()),
        "label_mismatch": int(label_mismatch_mask.sum()),
        "non_standard": int(non_standard_mask.sum()),
        "table": status_table,
        "issue_mask": issue_mask,
    }


def calculate_quality_score(total_rows, total_columns, issue_count):
    """Calculate a simple score where fewer issues means a higher score."""
    total_cells = max(total_rows * total_columns, 1)
    issue_rate = min(issue_count / total_cells, 1)

    return round((1 - issue_rate) * 100, 1)


def score_label(score):
    """Convert the numeric score into a simple readiness label."""
    if score >= 95:
        return "Launch ready"
    if score >= 85:
        return "Needs light cleanup"
    if score >= 70:
        return "Needs focused cleanup"

    return "Migration risk"


def build_recommendations(
    missing_by_column,
    duplicate_rows,
    duplicate_id_count,
    invalid_emails,
    invalid_phones,
    date_results,
    status_results,
):
    """Create plain-English recommendations based on detected problems."""
    recommendations = []

    columns_with_missing_values = missing_by_column[missing_by_column > 0]
    if not columns_with_missing_values.empty:
        columns = ", ".join(columns_with_missing_values.index.tolist())
        recommendations.append(
            {
                "priority": "High",
                "title": "Complete required fields",
                "detail": f"Review missing values in: {columns}.",
            }
        )

    if duplicate_rows > 0 or duplicate_id_count > 0:
        recommendations.append(
            {
                "priority": "High",
                "title": "Resolve duplicate customer records",
                "detail": "Deduplicate exact rows and duplicate customer IDs before migration.",
            }
        )

    for column, count in invalid_emails.items():
        if count > 0:
            recommendations.append(
                {
                    "priority": "Medium",
                    "title": "Repair email addresses",
                    "detail": f"Standardize or correct {count} invalid email values in {column}.",
                }
            )

    for column, count in invalid_phones.items():
        if count > 0:
            recommendations.append(
                {
                    "priority": "Medium",
                    "title": "Standardize phone numbers",
                    "detail": f"Clean {count} phone values in {column} to a consistent format.",
                }
            )

    for column, result in date_results.items():
        if result["missing"] > 0 or result["invalid"] > 0:
            recommendations.append(
                {
                    "priority": "Medium",
                    "title": "Normalize date fields",
                    "detail": f"Fix missing or invalid date values in {column}.",
                }
            )

    status_issue_count = (
        status_results["missing"]
        + status_results["label_mismatch"]
        + status_results["non_standard"]
    )
    if status_issue_count > 0:
        recommendations.append(
            {
                "priority": "Low",
                "title": "Create a status dictionary",
                "detail": "Map onboarding status values to one approved list before operational reporting.",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "priority": "Low",
                "title": "Data looks ready",
                "detail": "No major data quality issues were found. This dataset is ready for analysis.",
            }
        )

    return recommendations


def inject_css():
    """Add a polished visual system using Streamlit-friendly CSS."""
    st.markdown(
        """
        <style>
        :root {
            --page: #050816;
            --panel: #0b1220;
            --panel-soft: #111c31;
            --panel-raised: #14213d;
            --ink: #f8fafc;
            --muted: #b8c4d8;
            --line: #25466f;
            --blue: #2563eb;
            --blue-soft: #38bdf8;
            --yellow: #facc15;
            --yellow-soft: #fde68a;
            --coral: #fb7185;
        }

        .stApp,
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.24), transparent 30rem),
                linear-gradient(180deg, #050816 0%, #08111f 54%, #050816 100%);
            color: var(--ink);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: #020617;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] * {
            color: var(--ink);
        }

        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: 0;
        }

        p, label, span {
            color: inherit;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, var(--panel-raised), var(--panel));
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
        }

        div[data-testid="stMetricLabel"] {
            color: var(--muted);
        }

        div[data-testid="stMetricValue"] {
            color: var(--yellow);
        }

        [data-baseweb="tab-list"] {
            gap: 0.35rem;
            border-bottom: 1px solid var(--line);
        }

        button[data-baseweb="tab"] {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px 8px 0 0;
            color: var(--muted);
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: #0f2a55;
            border-color: var(--blue-soft);
            color: var(--yellow);
        }

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }

        [data-testid="stCaptionContainer"] {
            color: var(--muted);
        }

        .hero {
            background:
                linear-gradient(135deg, rgba(2, 6, 23, 0.98), rgba(15, 42, 85, 0.98)),
                linear-gradient(90deg, rgba(250, 204, 21, 0.45), rgba(37, 99, 235, 0.42));
            color: var(--ink);
            border-radius: 8px;
            padding: 1.6rem 1.8rem;
            border: 1px solid rgba(56, 189, 248, 0.36);
            margin-bottom: 1.2rem;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.32);
        }

        .hero-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 1.4rem;
            align-items: center;
        }

        .hero h1 {
            color: var(--yellow);
            font-size: 2.1rem;
            line-height: 1.12;
            margin: 0 0 0.45rem 0;
        }

        .hero p {
            color: #dbeafe;
            margin: 0;
            max-width: 760px;
        }

        .source-pill {
            background: rgba(250, 204, 21, 0.11);
            border: 1px solid rgba(250, 204, 21, 0.45);
            border-radius: 999px;
            color: var(--yellow-soft);
            padding: 0.55rem 0.8rem;
            white-space: nowrap;
            font-size: 0.86rem;
        }

        .score-panel {
            background: linear-gradient(180deg, var(--panel-raised), var(--panel));
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1.25rem;
            box-shadow: 0 18px 44px rgba(0, 0, 0, 0.30);
        }

        .score-ring {
            width: 176px;
            height: 176px;
            border-radius: 50%;
            background: conic-gradient(var(--yellow) calc(var(--score) * 1%), #1e293b 0);
            display: grid;
            place-items: center;
            margin: 0 auto 1rem auto;
            box-shadow: 0 0 0 8px rgba(37, 99, 235, 0.18);
        }

        .score-ring-inner {
            width: 126px;
            height: 126px;
            border-radius: 50%;
            background: #050816;
            display: grid;
            place-items: center;
            text-align: center;
            box-shadow: inset 0 0 0 1px var(--line);
        }

        .score-number {
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--yellow);
            line-height: 1;
        }

        .score-caption {
            color: var(--muted);
            font-size: 0.8rem;
            margin-top: 0.2rem;
        }

        .briefing-card,
        .recommendation-card,
        .check-card {
            background: linear-gradient(180deg, var(--panel-soft), var(--panel));
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 16px 34px rgba(0, 0, 0, 0.24);
            margin-bottom: 0.75rem;
        }

        .briefing-title,
        .recommendation-title,
        .check-title {
            color: var(--ink);
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        .briefing-copy,
        .recommendation-copy,
        .check-copy {
            color: var(--muted);
            font-size: 0.92rem;
            margin: 0;
        }

        .tag-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.75rem;
        }

        .tag {
            border-radius: 999px;
            padding: 0.25rem 0.6rem;
            font-size: 0.78rem;
            background: rgba(37, 99, 235, 0.18);
            color: #dbeafe;
            border: 1px solid rgba(56, 189, 248, 0.38);
        }

        .priority-high {
            border-left: 5px solid var(--coral);
        }

        .priority-medium {
            border-left: 5px solid var(--yellow);
        }

        .priority-low {
            border-left: 5px solid var(--blue-soft);
        }

        .chart-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.6rem 0 1.1rem 0;
        }

        .legend-item {
            align-items: center;
            background: rgba(11, 18, 32, 0.84);
            border: 1px solid var(--line);
            border-radius: 999px;
            color: var(--muted);
            display: inline-flex;
            font-size: 0.78rem;
            gap: 0.4rem;
            padding: 0.25rem 0.55rem;
        }

        .legend-swatch {
            border-radius: 999px;
            display: inline-block;
            height: 0.65rem;
            width: 0.65rem;
        }

        @media (max-width: 760px) {
            .hero-grid {
                grid-template-columns: 1fr;
            }

            .source-pill {
                white-space: normal;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(source_name):
    """Render the dashboard's opening panel."""
    safe_source = html.escape(source_name)
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-grid">
                <div>
                    <h1>Data Quality Monitoring Dashboard</h1>
                    <p>Audit customer migration readiness, isolate the messy records, and turn data cleanup into a focused handoff plan.</p>
                </div>
                <div class="source-pill">Source: {safe_source}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_score_panel(quality_score, issue_count):
    """Render a visual quality score card."""
    safe_label = html.escape(score_label(quality_score))
    st.markdown(
        f"""
        <div class="score-panel">
            <div class="score-ring" style="--score: {quality_score};">
                <div class="score-ring-inner">
                    <div>
                        <div class="score-number">{quality_score}%</div>
                        <div class="score-caption">Quality score</div>
                    </div>
                </div>
            </div>
            <div class="briefing-title">{safe_label}</div>
            <p class="briefing-copy">{issue_count:,} issue signals found across this dataset.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_briefing_card(title, copy, tags):
    """Render a compact insight card."""
    safe_title = html.escape(title)
    safe_copy = html.escape(copy)
    safe_tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in tags)

    st.markdown(
        f"""
        <div class="briefing-card">
            <div class="briefing-title">{safe_title}</div>
            <p class="briefing-copy">{safe_copy}</p>
            <div class="tag-row">{safe_tags}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_check_card(title, copy):
    """Render a short quality check summary."""
    st.markdown(
        f"""
        <div class="check-card">
            <div class="check-title">{html.escape(title)}</div>
            <p class="check-copy">{html.escape(copy)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendation_card(recommendation):
    """Render one recommendation with visual priority."""
    priority = recommendation["priority"].lower()
    st.markdown(
        f"""
        <div class="recommendation-card priority-{html.escape(priority)}">
            <div class="recommendation-title">{html.escape(recommendation["priority"])} priority: {html.escape(recommendation["title"])}</div>
            <p class="recommendation-copy">{html.escape(recommendation["detail"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_issue_summary(
    missing_values,
    duplicate_rows,
    duplicate_id_count,
    invalid_email_count,
    invalid_phone_count,
    invalid_date_count,
    status_issue_count,
):
    """Build a chart-ready issue summary."""
    issue_summary = pd.DataFrame(
        [
            {"Issue": "Missing values", "Count": missing_values},
            {"Issue": "Duplicate rows", "Count": duplicate_rows},
            {"Issue": "Duplicate IDs", "Count": duplicate_id_count},
            {"Issue": "Invalid emails", "Count": invalid_email_count},
            {"Issue": "Invalid phones", "Count": invalid_phone_count},
            {"Issue": "Date issues", "Count": invalid_date_count},
            {"Issue": "Status issues", "Count": status_issue_count},
        ]
    )

    return add_chart_colors(issue_summary, "Issue", ISSUE_COLORS)


def add_chart_colors(df, label_column, color_map=None):
    """Attach a color column so Streamlit charts use distinct colors."""
    colored_df = df.copy()
    color_map = color_map or {}
    colors = []

    for index, label in enumerate(colored_df[label_column]):
        colors.append(color_map.get(label, CHART_PALETTE[index % len(CHART_PALETTE)]))

    colored_df["Color"] = colors

    return colored_df


def series_to_colored_chart(series, label_column, value_column, color_map=None):
    """Convert a Pandas Series into colored chart data."""
    chart_df = series.reset_index()
    chart_df.columns = [label_column, value_column]

    return add_chart_colors(chart_df, label_column, color_map)


def render_chart_legend(chart_df, label_column, color_column, value_column=None):
    """Render a compact legend for custom chart colors."""
    legend_items = []

    for _, row in chart_df.iterrows():
        label = html.escape(str(row[label_column]))
        color = html.escape(str(row[color_column]))
        value = ""

        if value_column is not None:
            value = f" ({int(row[value_column]):,})"

        legend_items.append(
            f'<span class="legend-item"><span class="legend-swatch" style="background: {color};"></span>{label}{value}</span>'
        )

    st.markdown(
        f'<div class="chart-legend">{"".join(legend_items)}</div>',
        unsafe_allow_html=True,
    )


def build_issue_masks(
    df,
    missing_by_cell,
    duplicate_row_mask,
    duplicate_id_mask,
    email_masks,
    phone_masks,
    date_results,
    status_results,
):
    """Create row-level masks for filtering the preview table."""
    false_mask = pd.Series(False, index=df.index)
    missing_mask = missing_by_cell.any(axis=1) if not df.empty else false_mask
    email_mask = combine_masks(email_masks.values(), df.index)
    phone_mask = combine_masks(phone_masks.values(), df.index)
    date_mask = combine_masks(
        [
            result["missing_mask"] | result["invalid_mask"]
            for result in date_results.values()
        ],
        df.index,
    )
    contact_mask = email_mask | phone_mask
    status_mask = status_results["issue_mask"]
    any_issue_mask = (
        missing_mask
        | duplicate_row_mask
        | duplicate_id_mask
        | contact_mask
        | date_mask
        | status_mask
    )

    return {
        "All quality issues": any_issue_mask,
        "Missing values": missing_mask,
        "Duplicate records": duplicate_row_mask | duplicate_id_mask,
        "Contact details": contact_mask,
        "Date fields": date_mask,
        "Status consistency": status_mask,
    }


def combine_masks(masks, index):
    """Combine several boolean masks into one mask."""
    combined_mask = pd.Series(False, index=index)

    for mask in masks:
        combined_mask = combined_mask | mask

    return combined_mask


def build_preview_table(df, issue_masks):
    """Add issue tags to the dataset for easier review."""
    preview_df = df.copy()
    issue_tags = []

    for row_index in df.index:
        row_tags = [
            issue_name
            for issue_name, mask in issue_masks.items()
            if issue_name != "All quality issues" and bool(mask.loc[row_index])
        ]
        issue_tags.append(", ".join(row_tags) if row_tags else "No issue detected")

    preview_df.insert(0, "issue_tags", issue_tags)

    return preview_df


def show_overview(
    df,
    quality_score,
    issue_count,
    issue_summary,
    missing_by_column,
    date_results,
):
    """Display the main overview section."""
    left_column, right_column = st.columns([0.34, 0.66], gap="large")

    with left_column:
        render_score_panel(quality_score, issue_count)

    with right_column:
        metric_columns = st.columns(4)
        metric_columns[0].metric("Rows", f"{len(df):,}")
        metric_columns[1].metric("Columns", f"{len(df.columns):,}")
        metric_columns[2].metric("Issue Signals", f"{issue_count:,}")
        metric_columns[3].metric("Ready Label", score_label(quality_score))

        render_briefing_card(
            "Migration briefing",
            "Use the issue filters to move from overall health to the exact customer records that need cleanup.",
            ["CSV upload", "Data QA", "Onboarding workflow"],
        )

    chart_columns = st.columns(2, gap="large")

    with chart_columns[0]:
        st.subheader("Issue Mix")
        st.bar_chart(
            issue_summary,
            x="Issue",
            y="Count",
            color="Color",
            horizontal=True,
            height=320,
        )
        render_chart_legend(issue_summary, "Issue", "Color", "Count")

    with chart_columns[1]:
        st.subheader("Missing Values by Column")
        missing_chart = series_to_colored_chart(
            missing_by_column,
            "Column",
            "Missing Values",
        )
        st.bar_chart(
            missing_chart,
            x="Column",
            y="Missing Values",
            color="Color",
            height=320,
        )
        render_chart_legend(missing_chart, "Column", "Color", "Missing Values")

    lower_columns = st.columns(2, gap="large")

    with lower_columns[0]:
        if "onboarding_status" in df.columns:
            st.subheader("Onboarding Status Distribution")
            status_counts = df["onboarding_status"].fillna("Missing").replace("", "Blank").value_counts()
            status_chart = series_to_colored_chart(status_counts, "Status", "Records")
            st.bar_chart(
                status_chart,
                x="Status",
                y="Records",
                color="Color",
                height=320,
            )
            render_chart_legend(status_chart, "Status", "Color", "Records")
        else:
            st.info("No onboarding_status column was detected.")

    with lower_columns[1]:
        show_date_trend(date_results)


def show_date_trend(date_results):
    """Show record counts over time for the first detected date column."""
    if not date_results:
        st.info("No date column was detected.")
        return

    first_date_column = next(iter(date_results))
    parsed_dates = date_results[first_date_column]["parsed_dates"].dropna()

    if parsed_dates.empty:
        st.info(f"No valid dates were found in {first_date_column}.")
        return

    st.subheader(f"Records Over Time by {first_date_column}")
    monthly_counts = parsed_dates.dt.to_period("M").value_counts().sort_index()
    monthly_counts.index = monthly_counts.index.astype(str)
    monthly_chart = monthly_counts.reset_index()
    monthly_chart.columns = ["Month", "Records"]
    st.line_chart(monthly_chart, x="Month", y="Records", color="#facc15", height=320)


def show_data_preview(df, issue_masks, preview_rows):
    """Display an interactive data preview with issue filtering."""
    focus_area = st.selectbox("Investigate", list(issue_masks.keys()))
    show_only_flagged = st.toggle("Show only flagged rows", value=True)

    preview_df = build_preview_table(df, issue_masks)
    focus_mask = issue_masks[focus_area]

    if show_only_flagged:
        preview_df = preview_df[focus_mask]

    st.caption(f"Showing {len(preview_df):,} of {len(df):,} records.")
    st.dataframe(preview_df.head(preview_rows), width="stretch", hide_index=True)


def show_quality_checks(
    df,
    missing_by_column,
    duplicate_rows,
    duplicate_id_count,
    email_columns,
    phone_columns,
    invalid_emails,
    invalid_phones,
    date_results,
    status_results,
):
    """Display quality checks in a focused investigation area."""
    check_tabs = st.tabs(["Missing", "Duplicates", "Contact", "Dates", "Statuses"])

    with check_tabs[0]:
        render_check_card(
            "Missing values",
            f"{int(missing_by_column.sum()):,} blank or missing values were found.",
        )
        missing_table = missing_by_column.reset_index()
        missing_table.columns = ["Column", "Missing Values"]
        st.dataframe(missing_table, width="stretch", hide_index=True)

    with check_tabs[1]:
        render_check_card(
            "Duplicate records",
            f"{duplicate_rows:,} exact duplicate rows and {duplicate_id_count:,} duplicate customer IDs were found.",
        )
        if duplicate_rows > 0:
            st.dataframe(df[df.duplicated(keep=False)], width="stretch", hide_index=True)
        elif duplicate_id_count > 0 and "customer_id" in df.columns:
            st.dataframe(df[df["customer_id"].duplicated(keep=False)], width="stretch", hide_index=True)
        else:
            st.success("No duplicate rows or duplicate customer IDs were found.")

    with check_tabs[2]:
        contact_rows = []
        for column in email_columns:
            contact_rows.append(
                {
                    "Column": column,
                    "Check": "Invalid email format",
                    "Issue Count": invalid_emails.get(column, 0),
                }
            )
        for column in phone_columns:
            contact_rows.append(
                {
                    "Column": column,
                    "Check": "Invalid phone format",
                    "Issue Count": invalid_phones.get(column, 0),
                }
            )

        if contact_rows:
            render_check_card(
                "Contact checks",
                "Email and phone values are checked with simple beginner-friendly patterns.",
            )
            st.dataframe(pd.DataFrame(contact_rows), width="stretch", hide_index=True)
        else:
            st.info("No email or phone column was detected.")

    with check_tabs[3]:
        if date_results:
            date_table = pd.DataFrame(
                [
                    {
                        "Date Column": column,
                        "Missing Dates": result["missing"],
                        "Invalid Dates": result["invalid"],
                    }
                    for column, result in date_results.items()
                ]
            )
            render_check_card(
                "Date checks",
                "Date fields are checked for missing values and values Pandas cannot parse.",
            )
            st.dataframe(date_table, width="stretch", hide_index=True)
        else:
            st.info("No date column was detected.")

    with check_tabs[4]:
        if "onboarding_status" in df.columns:
            status_issue_count = (
                status_results["missing"]
                + status_results["label_mismatch"]
                + status_results["non_standard"]
            )
            render_check_card(
                "Status consistency",
                f"{status_issue_count:,} onboarding status values need standardization or review.",
            )
            st.dataframe(status_results["table"], width="stretch", hide_index=True)
        else:
            st.info("No onboarding_status column was detected.")


def show_recommendations(recommendations, issue_summary):
    """Display recommendations and an issue backlog."""
    left_column, right_column = st.columns([0.58, 0.42], gap="large")

    with left_column:
        st.subheader("Cleanup Playbook")
        for recommendation in recommendations:
            render_recommendation_card(recommendation)

    with right_column:
        st.subheader("Issue Backlog")
        backlog = issue_summary[issue_summary["Count"] > 0].sort_values("Count", ascending=False)

        if backlog.empty:
            st.success("No issue backlog. Nice and quiet.")
        else:
            st.dataframe(backlog, width="stretch", hide_index=True)


def main():
    st.set_page_config(
        page_title="Data Quality Monitoring Dashboard",
        layout="wide",
    )
    inject_css()

    st.sidebar.header("Data Source")
    uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"])
    preview_rows = st.sidebar.slider("Preview rows", min_value=10, max_value=50, value=25, step=5)

    try:
        df, source_name = load_data(uploaded_file)
    except FileNotFoundError:
        st.error(f"Sample file was not found at {SAMPLE_FILE}.")
        st.stop()
    except pd.errors.EmptyDataError:
        st.error("The selected CSV file is empty. Please upload a file with data.")
        st.stop()
    except Exception as error:
        st.error(f"Could not load the CSV file: {error}")
        st.stop()

    if df.empty:
        st.warning("The dataset loaded successfully, but it does not contain any rows.")

    st.sidebar.success(f"Loaded: {source_name}")
    render_hero(source_name)

    total_rows = len(df)
    total_columns = len(df.columns)
    duplicate_rows = int(df.duplicated().sum())
    duplicate_row_mask = df.duplicated(keep=False)

    if "customer_id" in df.columns:
        duplicate_id_count = int(df["customer_id"].duplicated().sum())
        duplicate_id_mask = df["customer_id"].duplicated(keep=False)
    else:
        duplicate_id_count = 0
        duplicate_id_mask = pd.Series(False, index=df.index)

    missing_by_cell = df.apply(get_blank_mask)
    missing_by_column = missing_by_cell.sum()
    missing_values = int(missing_by_column.sum())

    email_columns = find_columns(df, ["email", "e-mail"])
    phone_columns = find_columns(df, ["phone", "mobile", "telephone", "contact"])
    date_columns = find_columns(df, ["date", "dob", "birth", "created", "updated", "joined"])

    invalid_emails, email_masks = check_email_values(df, email_columns)
    invalid_phones, phone_masks = check_phone_values(df, phone_columns)
    date_results = check_date_values(df, date_columns)
    status_results = check_status_values(df)

    invalid_email_count = sum(invalid_emails.values())
    invalid_phone_count = sum(invalid_phones.values())
    invalid_date_count = sum(result["missing"] + result["invalid"] for result in date_results.values())
    status_issue_count = (
        status_results["missing"]
        + status_results["label_mismatch"]
        + status_results["non_standard"]
    )
    issue_count = (
        missing_values
        + duplicate_rows
        + duplicate_id_count
        + invalid_email_count
        + invalid_phone_count
        + invalid_date_count
        + status_issue_count
    )
    quality_score = calculate_quality_score(total_rows, total_columns, issue_count)

    issue_summary = build_issue_summary(
        missing_values,
        duplicate_rows,
        duplicate_id_count,
        invalid_email_count,
        invalid_phone_count,
        invalid_date_count,
        status_issue_count,
    )
    issue_masks = build_issue_masks(
        df,
        missing_by_cell,
        duplicate_row_mask,
        duplicate_id_mask,
        email_masks,
        phone_masks,
        date_results,
        status_results,
    )
    recommendations = build_recommendations(
        missing_by_column,
        duplicate_rows,
        duplicate_id_count,
        invalid_emails,
        invalid_phones,
        date_results,
        status_results,
    )

    overview_tab, preview_tab, checks_tab, recommendations_tab = st.tabs(
        ["Overview", "Data Preview", "Quality Checks", "Recommendations"]
    )

    with overview_tab:
        show_overview(
            df,
            quality_score,
            issue_count,
            issue_summary,
            missing_by_column,
            date_results,
        )

    with preview_tab:
        show_data_preview(df, issue_masks, preview_rows)

    with checks_tab:
        show_quality_checks(
            df,
            missing_by_column,
            duplicate_rows,
            duplicate_id_count,
            email_columns,
            phone_columns,
            invalid_emails,
            invalid_phones,
            date_results,
            status_results,
        )

    with recommendations_tab:
        show_recommendations(recommendations, issue_summary)


if __name__ == "__main__":
    main()
