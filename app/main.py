from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.errors import AccessDeniedError
from app.web.api.routes import router as api_router
from app.web.jinja.routes import router as jinja_router

app = FastAPI(title="fastapi_projecr")

# Session middleware для flash-сообщений
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "web" / "jinja" / "templates"))

# Добавляем глобальную функцию для получения количества непрочитанных
def _get_unread_count(request: Request) -> int:
    """Получить количество непрочитанных сообщений для текущего агента."""
    agent = getattr(request.state, 'agent', None)
    if not agent:
        print(f"[UNREAD] No agent in request.state")
        return 0
    
    from app.models import get_db
    from app.services.ticket.read_state_service import TicketReadStateService
    
    db = next(get_db())
    try:
        read_state_service = TicketReadStateService(db)
        count = read_state_service.get_total_unread_for_agent(agent_id=agent.id)
        print(f"[UNREAD] Agent {agent.id} ({agent.login}): {count} unread messages")
        return count
    except Exception as e:
        print(f"[UNREAD] Error: {e}")
        return 0
    finally:
        db.close()

templates.env.globals["get_unread_count"] = _get_unread_count


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений."""
    
    # 404 для скачивания файлов → HTML страница
    if exc.status_code == 404 and "/attachments/" in request.url.path and "/download" in request.url.path:
        from app.core.auth import get_current_agent_optional
        from app.models import get_db
        
        db = next(get_db())
        agent = get_current_agent_optional(request, db)
        
        # Извлекаем attachment_id из URL
        attachment_id = request.url.path.split("/attachments/")[1].split("/")[0] if "/attachments/" in request.url.path else None
        
        return templates.TemplateResponse(
            "error/file_not_found.html",
            {
                "request": request,
                "agent": agent,
                "attachment_id": attachment_id,
                "error_message": exc.detail,
            },
            status_code=404,
        )
    
    # 401 → редирект на /login
    if exc.status_code == 401:
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=401, content={"detail": exc.detail})
        next_url = quote(str(request.url))
        return RedirectResponse(
            url=f"/login?next={next_url}",
            status_code=303,
        )
    
    # Остальные 404 → JSON
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

