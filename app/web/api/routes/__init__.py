from __future__ import annotations

from fastapi import APIRouter

from .bans import router as bans_router
from .tickets import router as tickets_router

router = APIRouter(prefix="/api", tags=["api"])

router.include_router(bans_router)
router.include_router(tickets_router)


@router.get("/health")
def health() -> dict[str, str]:
    # Simple health endpoint placeholder.
    return {"status": "ok"}

