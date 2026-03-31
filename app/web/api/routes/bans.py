"""
API роуты для управления банами (email и IP).

Требует авторизации (агент).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.auth import CurrentAgent
from app.models import get_db
from app.models.agent import Agent
from app.services.ban_service import BanService
from app.services.utils import ip_to_int, int_to_ip, ip_to_display


router = APIRouter(prefix="/bans", tags=["bans"])


# === Схемы ===

class EmailBanCreate(BaseModel):
    email: str = Field(..., description="Email для блокировки")
    reason: Optional[str] = Field(None, description="Причина бана")


class EmailBanResponse(BaseModel):
    id: int
    email: str
    banned_by: Optional[int]
    reason: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class IPBanCreate(BaseModel):
    ip_from: str = Field(..., description="Начальный IP диапазона (или одиночный IP)")
    ip_to: Optional[str] = Field(None, description="Конечный IP диапазона")
    ip_display: Optional[str] = Field(None, description="Человекочитаемое представление")


class IPBanResponse(BaseModel):
    id: int
    ip_from: int
    ip_to: int
    ip_display: str
    banned_by: Optional[int]
    created_at: str
    
    class Config:
        from_attributes = True


# === Email баны ===

@router.get("/emails", response_model=List[EmailBanResponse])
def get_banned_emails(
    request: Request,
    db: Session = Depends(get_db),
    agent: CurrentAgent = None,
):
    """Получить все забаненные email."""
    return BanService.get_banned_emails(db)


@router.post("/emails", response_model=EmailBanResponse)
def ban_email(
    request: Request,
    data: EmailBanCreate,
    db: Session = Depends(get_db),
    agent: CurrentAgent = None,
):
    """
    Добавить email в бан-лист.
    
    Требуется авторизация (агент).
    """
    try:
        banned = BanService.add_email_ban(
            db=db,
            email=data.email,
            banned_by=agent.id,
            reason=data.reason,
        )
        return banned
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/emails/{ban_id}")
def unban_email(
    ban_id: int,
    request: Request,
    db: Session = Depends(get_db),
    agent: CurrentAgent = None,
):
    """Удалить бан по email."""
    success = BanService.remove_email_ban(db, ban_id)
    if not success:
        raise HTTPException(status_code=404, detail="Бан не найден")
    return {"success": True}


# === IP баны ===

@router.get("/ips", response_model=List[IPBanResponse])
def get_banned_ips(
    request: Request,
    db: Session = Depends(get_db),
    agent: CurrentAgent = None,
):
    """Получить все забаненные IP (диапазоны)."""
    return BanService.get_banned_ips(db)


@router.post("/ips", response_model=IPBanResponse)
def ban_ip(
    request: Request,
    data: IPBanCreate,
    db: Session = Depends(get_db),
    agent: CurrentAgent = None,
):
    """
    Добавить IP или диапазон IP в бан-лист.

    Требуется авторизация (агент).

    Если ip_to не указан, блокируется одиночный IP.
    """
    try:
        # Валидация IP
        ip_to_int(data.ip_from)
        if data.ip_to:
            ip_to_int(data.ip_to)

        banned = BanService.add_ip_ban(
            db=db,
            ip_from=data.ip_from,
            ip_to=data.ip_to,
            banned_by=agent.id,
            ip_display=data.ip_display,
        )
        return banned
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Неверный IP: {e}")


@router.delete("/ips/{ban_id}")
def unban_ip(
    ban_id: int,
    request: Request,
    db: Session = Depends(get_db),
    agent: CurrentAgent = None,
):
    """Удалить бан по IP."""
    success = BanService.remove_ip_ban(db, ban_id)
    if not success:
        raise HTTPException(status_code=404, detail="Бан не найден")
    return {"success": True}


# === Утилиты ===

@router.get("/check")
def check_ban(
    email: Optional[str] = None,
    ip: Optional[str] = None,
    db: Session = Depends(get_db),
    agent: CurrentAgent = None,
):
    """
    Проверить, забанены ли email или IP.
    
    Возвращает статус бана для переданных параметров.
    """
    result = {
        "email": None,
        "ip": None,
        "email_banned": False,
        "ip_banned": False,
    }
    
    if email:
        result["email"] = email
        result["email_banned"] = BanService.is_email_banned(db, email)
    
    if ip:
        try:
            ip_to_int(ip)
            result["ip"] = ip
            result["ip_banned"] = BanService.is_ip_banned(db, ip)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат IP")
    
    return result
