"""Production entry point: serves the API under /api and the built React website at /.

In development, Vite serves the website and forwards /api to the backend instead (see frontend/vite.config.js),
so locally you keep running `uvicorn app.main:app`.
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.main import app as api

STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))

app = FastAPI(title="RepoGrill", lifespan=api.router.lifespan_context)
app.mount("/api", api)
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="website")
