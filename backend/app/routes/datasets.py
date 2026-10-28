import io
import json
import re
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import MAX_STORED_ISSUES, MAX_UPLOAD_MB, SAMPLE_FILE, UPLOAD_DIR
from ..database import get_db
from ..models import Dataset, Issue, Report, User
from ..schemas import DatasetDetail, DatasetSummary
from ..services.cleaning import clean_dataframe
from ..services.quality_checks import analyze

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

ALLOWED_RULE_KEYS = {"email_columns", "phone_columns", "date_columns", "id_column", "status_column"}


# ---------------------------------------------------------------- helpers

def parse_csv(content: bytes) -> pd.DataFrame:
    """Read CSV bytes into a DataFrame, with friendly errors."""
    if not content.strip():
        raise HTTPException(400, "The file is empty.")
    last_error = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
        except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as exc:
            raise HTTPException(400, f"Could not read this CSV: {exc}")
    else:
        raise HTTPException(400, f"Could not decode this file: {last_error}")
    if df.empty or len(df.columns) == 0:
        raise HTTPException(400, "The CSV has no data rows.")
    return df


def parse_rules(raw):
    if not raw:
        return None
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(400, "Rules must be valid JSON.")
    if not isinstance(rules, dict) or not set(rules) <= ALLOWED_RULE_KEYS:
        raise HTTPException(400, f"Rules may only contain: {', '.join(sorted(ALLOWED_RULE_KEYS))}.")
    return rules


def summary_of(dataset: Dataset, user: User) -> dict:
    report = dataset.report
    return {
        "id": dataset.id,
        "filename": dataset.filename,
        "uploaded_at": dataset.uploaded_at,
        "total_rows": dataset.total_rows,
        "total_columns": dataset.total_columns,
        "quality_score": report.quality_score,
        "score_label": report.score_label,
        "issue_count": report.issue_count,
        "below_threshold": report.quality_score < user.alert_threshold,
    }


def get_owned_dataset(dataset_id: int, user: User, db: Session) -> Dataset:
    """Fetch a dataset only if it belongs to this user (others get a plain 404)."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.owner_id != user.id:
        raise HTTPException(404, "Dataset not found.")
    return dataset


def load_stored_dataframe(dataset: Dataset) -> pd.DataFrame:
    path = Path(dataset.stored_path)
    if not path.exists():
        raise HTTPException(410, "The stored file is no longer available.")
    return parse_csv(path.read_bytes())


def create_dataset(db: Session, user: User, filename: str, content: bytes, rules) -> Dataset:
    df = parse_csv(content)
    report_data, issues = analyze(df, rules, issue_limit=MAX_STORED_ISSUES)

    folder = UPLOAD_DIR / str(user.id)
    folder.mkdir(parents=True, exist_ok=True)
    stored_path = folder / f"{uuid.uuid4().hex}.csv"
    stored_path.write_bytes(content)

    dataset = Dataset(owner_id=user.id, filename=Path(filename).name[:255] or "upload.csv",
                      stored_path=str(stored_path), total_rows=len(df), total_columns=len(df.columns))
    db.add(dataset)
    db.flush()  # gives the dataset an id
    db.add(Report(dataset_id=dataset.id, quality_score=report_data["quality_score"],
                  score_label=report_data["score_label"], issue_count=report_data["issue_count"],
                  data=report_data))
    db.bulk_insert_mappings(Issue, [{**issue, "dataset_id": dataset.id} for issue in issues])
    db.commit()
    db.refresh(dataset)
    return dataset


# ---------------------------------------------------------------- routes

@router.post("", response_model=DatasetDetail, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    rules: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {MAX_UPLOAD_MB} MB.")
    dataset = create_dataset(db, user, file.filename, content, parse_rules(rules))
    return {**summary_of(dataset, user), "report": dataset.report.data}


@router.post("/sample", response_model=DatasetDetail, status_code=201)
def upload_sample(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Analyze the bundled demo file, so new users can try the app instantly."""
    dataset = create_dataset(db, user, SAMPLE_FILE.name, SAMPLE_FILE.read_bytes(), None)
    return {**summary_of(dataset, user), "report": dataset.report.data}


@router.get("", response_model=list[DatasetSummary])
def list_datasets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    datasets = (db.query(Dataset).filter(Dataset.owner_id == user.id)
                .order_by(Dataset.uploaded_at.desc(), Dataset.id.desc()).all())
    return [summary_of(d, user) for d in datasets]


@router.get("/trends")
def score_trends(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Score history, grouped by file name. Re-upload the same file name to see progress."""
    datasets = (db.query(Dataset).filter(Dataset.owner_id == user.id)
                .order_by(Dataset.uploaded_at.asc(), Dataset.id.asc()).all())
    groups: dict[str, list] = {}
    for d in datasets:
        groups.setdefault(d.filename, []).append(
            {"id": d.id, "uploaded_at": d.uploaded_at.isoformat(), "score": d.report.quality_score})
    series = [{"filename": name, "points": points} for name, points in groups.items()]
    series.sort(key=lambda s: len(s["points"]), reverse=True)
    return series


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = get_owned_dataset(dataset_id, user, db)
    return {**summary_of(dataset, user), "report": dataset.report.data}


@router.get("/{dataset_id}/issues")
def list_issues(
    dataset_id: int,
    issue_type: str | None = None,
    column: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_dataset(dataset_id, user, db)
    query = db.query(Issue).filter(Issue.dataset_id == dataset_id)
    if issue_type:
        query = query.filter(Issue.issue_type == issue_type)
    if column:
        query = query.filter(Issue.column_name == column)
    total = query.count()
    rows = (query.order_by(Issue.row_number, Issue.id)
            .offset((page - 1) * page_size).limit(page_size).all())
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [{"row_number": r.row_number, "column": r.column_name,
                   "issue_type": r.issue_type, "value": r.value} for r in rows],
    }


@router.get("/{dataset_id}/preview")
def preview_rows(
    dataset_id: int,
    rows: int = Query(25, ge=5, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """First rows of the file, plus which cells have problems (for highlighting)."""
    dataset = get_owned_dataset(dataset_id, user, db)
    df = load_stored_dataframe(dataset).head(rows)
    records = df.astype(object).where(df.notna(), None).to_dict(orient="records")

    flagged: dict[int, list] = {}
    issues = (db.query(Issue).filter(Issue.dataset_id == dataset_id,
                                     Issue.row_number <= rows + 1).all())
    for issue in issues:
        flagged.setdefault(issue.row_number, []).append(
            {"column": issue.column_name, "issue_type": issue.issue_type})

    return {
        "columns": [str(c) for c in df.columns],
        "rows": [{"row_number": i + 2, "values": {str(k): v for k, v in rec.items()},
                  "issues": flagged.get(i + 2, [])} for i, rec in enumerate(records)],
    }


@router.get("/{dataset_id}/cleaned")
def download_cleaned(dataset_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = get_owned_dataset(dataset_id, user, db)
    df = load_stored_dataframe(dataset)
    cleaned, _stats = clean_dataframe(df, dataset.report.data.get("rules") or None)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(dataset.filename).stem)
    return Response(
        content=cleaned.to_csv(index=False),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="cleaned_{safe_name}.csv"'},
    )


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dataset = get_owned_dataset(dataset_id, user, db)
    Path(dataset.stored_path).unlink(missing_ok=True)
    db.delete(dataset)
    db.commit()
    return Response(status_code=204)
