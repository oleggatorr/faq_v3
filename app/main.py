from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.web.api.routes import router as api_router
from app.web.jinja.routes import router as jinja_router

app = FastAPI(title="fastapi_projecr")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Для 401: HTML → редирект на /login, API → JSON 401."""
    if exc.status_code == 401:
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=401, content={"detail": exc.detail})
        next_url = quote(str(request.url))
        return RedirectResponse(
            url=f"/login?next={next_url}",
            status_code=303,
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Static files for Jinja2 templates (css/js placeholders).
static_dir = Path(__file__).resolve().parent / "web" / "jinja" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Separate routers by UI technology.
app.include_router(jinja_router)
app.include_router(api_router)

