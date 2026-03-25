from fastapi import APIRouter

from .categories import router as categories_router
from .languages import router as languages_router

router = APIRouter()
router.include_router(languages_router)
router.include_router(categories_router)

__all__ = ["router"]
