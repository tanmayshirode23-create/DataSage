"""Database tables."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    # Stored as naive UTC; the frontend adds "Z" when parsing.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    alert_threshold = Column(Float, nullable=False, default=70.0)
    created_at = Column(DateTime, default=utcnow)

    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")


class Dataset(Base):
    """One uploaded CSV file."""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    total_rows = Column(Integer, nullable=False)
    total_columns = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=utcnow, index=True)

    owner = relationship("User", back_populates="datasets")
    report = relationship("Report", back_populates="dataset", uselist=False, cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="dataset", cascade="all, delete-orphan")


class Report(Base):
    """The result of running all quality checks on one dataset."""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), unique=True, nullable=False)
    quality_score = Column(Float, nullable=False)
    score_label = Column(String(50), nullable=False)
    issue_count = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)  # charts, check details, recommendations

    dataset = relationship("Dataset", back_populates="report")


class Issue(Base):
    """One problem found in one spot of the file (a row, and usually a column)."""
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), index=True, nullable=False)
    row_number = Column(Integer, nullable=False)  # spreadsheet row; header is row 1
    column_name = Column(String(255), nullable=False)
    issue_type = Column(String(50), index=True, nullable=False)
    value = Column(String(255), nullable=False, default="")

    dataset = relationship("Dataset", back_populates="issues")
