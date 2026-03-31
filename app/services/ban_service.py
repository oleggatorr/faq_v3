"""
Сервис управления банами (email и IP).

Позволяет проверять и управлять заблокированными email и IP-адресами.
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from app.models.ban import BannedEmail, BannedIP
from app.services.utils import ip_to_int


class BanService:
    """Сервис для работы с банами."""

    @staticmethod
    def is_email_banned(db: Session, email: str) -> bool:
        """
        Проверить, забанен ли email.
        
        Args:
            db: Сессия базы данных
            email: Email для проверки
            
        Returns:
            True если email забанен
        """
        email = email.lower().strip()
        banned = db.query(BannedEmail).filter(
            BannedEmail.email == email
        ).first()
        return banned is not None

    @staticmethod
    def is_ip_banned(db: Session, ip: str) -> bool:
        """
        Проверить, забанен ли IP (поддерживает диапазоны).
        
        Args:
            db: Сессия базы данных
            ip: IP-адрес для проверки
            
        Returns:
            True если IP забанен
        """
        ip_int = ip_to_int(ip)
        # Проверяем все диапазоны банов
        banned_ips = db.query(BannedIP).all()
        for banned in banned_ips:
            if banned.ip_from <= ip_int <= banned.ip_to:
                return True
        return False

    @staticmethod
    def add_email_ban(
        db: Session,
        email: str,
        banned_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> BannedEmail:
        """
        Добавить email в бан-лист.
        
        Args:
            db: Сессия базы данных
            email: Email для блокировки
            banned_by: ID агента, который забанил (опционально)
            reason: Причина бана (опционально)
            
        Returns:
            Созданный объект BannedEmail
            
        Raises:
            ValueError: Если email уже забанен
        """
        email = email.lower().strip()
        
        # Проверка на дубликат
        existing = db.query(BannedEmail).filter(
            BannedEmail.email == email
        ).first()
        if existing:
            raise ValueError(f"Email '{email}' уже забанен")
        
        banned_email = BannedEmail(
            email=email,
            banned_by=banned_by,
            reason=reason,
        )
        db.add(banned_email)
        db.commit()
        db.refresh(banned_email)
        return banned_email

    @staticmethod
    def add_ip_ban(
        db: Session,
        ip_from: str,
        ip_to: Optional[str] = None,
        banned_by: Optional[int] = None,
        ip_display: Optional[str] = None,
    ) -> BannedIP:
        """
        Добавить IP или диапазон IP в бан-лист.
        
        Args:
            db: Сессия базы данных
            ip_from: Начальный IP диапазона (или одиночный IP)
            ip_to: Конечный IP диапазона (если None, используется ip_from)
            banned_by: ID агента, который забанил (опционально)
            ip_display: Человекочитаемое представление (опционально)
            
        Returns:
            Созданный объект BannedIP
        """
        if ip_to is None:
            ip_to = ip_from
        
        ip_from_int = ip_to_int(ip_from)
        ip_to_int_val = ip_to_int(ip_to)
        
        # Если ip_display не указан, генерируем его
        if ip_display is None:
            if ip_from == ip_to:
                ip_display = ip_from
            else:
                ip_display = f"{ip_from} - {ip_to}"
        
        banned_ip = BannedIP(
            ip_from=ip_from_int,
            ip_to=ip_to_int_val,
            ip_display=ip_display,
            banned_by=banned_by,
        )
        db.add(banned_ip)
        db.commit()
        db.refresh(banned_ip)
        return banned_ip

    @staticmethod
    def remove_email_ban(db: Session, ban_id: int) -> bool:
        """
        Удалить бан по email.
        
        Args:
            db: Сессия базы данных
            ban_id: ID записи о бане
            
        Returns:
            True если удалено, False если не найдено
        """
        banned = db.query(BannedEmail).filter(BannedEmail.id == ban_id).first()
        if not banned:
            return False
        db.delete(banned)
        db.commit()
        return True

    @staticmethod
    def remove_ip_ban(db: Session, ban_id: int) -> bool:
        """
        Удалить бан по IP.
        
        Args:
            db: Сессия базы данных
            ban_id: ID записи о бане
            
        Returns:
            True если удалено, False если не найдено
        """
        banned = db.query(BannedIP).filter(BannedIP.id == ban_id).first()
        if not banned:
            return False
        db.delete(banned)
        db.commit()
        return True

    @staticmethod
    def get_banned_emails(db: Session) -> list[BannedEmail]:
        """Получить все забаненные email."""
        return db.query(BannedEmail).order_by(BannedEmail.created_at.desc()).all()

    @staticmethod
    def get_banned_ips(db: Session) -> list[BannedIP]:
        """Получить все забаненные IP."""
        return db.query(BannedIP).order_by(BannedIP.created_at.desc()).all()
