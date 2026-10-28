"""Central place for settings. Every value can be overridden with an environment variable."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'dq.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
SAMPLE_FILE = BASE_DIR / "sample_data" / "sample_customer_data.csv"
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

MAX_UPLOAD_MB = 10          # reject bigger files
MAX_STORED_ISSUES = 20000   # cap on row-level issues saved per dataset
