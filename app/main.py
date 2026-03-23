from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.web.api.routes import router as api_router
from app.web.jinja.routes import router as jinja_router

app = FastAPI(title="fastapi_projecr")

# Static files for Jinja2 templates (css/js placeholders).
static_dir = Path(__file__).resolve().parent / "web" / "jinja" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Separate routers by UI technology.
app.include_router(jinja_router)
app.include_router(api_router)

