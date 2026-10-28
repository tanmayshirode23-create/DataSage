"""Shapes of the data that go in and out of the API."""
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupIn(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("name")
    @classmethod
    def name_ok(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name is required.")
        return v

    @field_validator("email")
    @classmethod
    def email_ok(cls, v):
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("password")
    @classmethod
    def password_ok(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class SettingsIn(BaseModel):
    alert_threshold: float

    @field_validator("alert_threshold")
    @classmethod
    def threshold_ok(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Threshold must be between 0 and 100.")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    alert_threshold: float


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DatasetSummary(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    total_rows: int
    total_columns: int
    quality_score: float
    score_label: str
    issue_count: int
    below_threshold: bool


class DatasetDetail(DatasetSummary):
    report: dict
