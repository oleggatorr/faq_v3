from fastapi import APIRouter

from .auth import router as auth_router
from .main import router as main_router
from .agents import router as agents_router
from .departments import router as departments_router
from .lookups import router as lookups_router
from .tickets import router as tickets_router
from .logs import router as logs_router

router = APIRouter()

router.include_router(main_router)
router.include_router(auth_router)
router.include_router(tickets_router)
router.include_router(agents_router)
router.include_router(departments_router)
router.include_router(lookups_router)
router.include_router(logs_router)

__all__ = ["router"]
