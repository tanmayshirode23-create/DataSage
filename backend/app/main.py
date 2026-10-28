"""App entry point. Run with:  uvicorn app.main:app --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .database import Base, engine
from .routes import auth, datasets

Base.metadata.create_all(bind=engine)  # create tables on first run

app = FastAPI(title="Data Quality Monitor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router)
app.include_router(datasets.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
