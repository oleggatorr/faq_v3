from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def health() -> dict[str, str]:
    # Simple health endpoint placeholder.
    return {"status": "ok"}

