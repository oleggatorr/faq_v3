from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.errors import AccessDeniedError
from app.web.api.routes import router as api_router
from app.web.jinja.routes import router as jinja_router

app = FastAPI(title="fastapi_projecr")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "web" / "jinja" / "templates"))


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


@app.exception_handler(AccessDeniedError)
async def access_denied_handler(request: Request, exc: AccessDeniedError):
    """Возвращает HTML-страницу 'Нет прав доступа'."""
    # Для API возвращаем JSON
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=403, content={"detail": exc.detail})
    
    # Для HTML возвращаем страницу
    from app.core.auth import get_current_agent_optional
    from app.models import get_db
    
    # Получаем агента (опционально)
    db = next(get_db())
    agent = get_current_agent_optional(request, db)  # Не await!
    
    # Получаем права агента
    permissions_dict = agent.get_permissions_dict() if agent else {}
    
    return templates.TemplateResponse(
        "error/access_denied.html",
        {
            "request": request,
            "agent": agent,
            "required_permission": exc.required_permission,
            "error": exc.detail,
            **permissions_dict,
        },
        status_code=403,
    )


# Static files for Jinja2 templates (css/js placeholders).
static_dir = Path(__file__).resolve().parent / "web" / "jinja" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Separate routers by UI technology.
app.include_router(jinja_router)
app.include_router(api_router)

