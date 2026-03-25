from __future__ import annotations

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate


class AuditLogService:
    """Сервис для работы с аудиторскими логами."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, log_data: AuditLogCreate) -> AuditLog:
        """Создать запись в логе."""
        db_log = AuditLog(**log_data.model_dump())
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        return db_log

    def log_action(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Быстрое логирование действия.
        
        Args:
            action: Тип действия (create, update, delete, login, logout)
            entity_type: Тип объекта (ticket, agent, department)
            entity_id: ID объекта
            agent_id: ID агента, выполнившего действие
            details: Дополнительные данные (будут преобразованы в JSON)
            ip_address: IP-адрес
            user_agent: User-Agent
        """
        import json
        
        details_json = json.dumps(details, ensure_ascii=False, default=str) if details else None
        
        log_data = AuditLogCreate(
            agent_id=agent_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details_json,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return self.create(log_data)

    def get_list(
        self,
        agent_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Получить список логов с фильтрацией."""
        query = self.db.query(AuditLog)
        
        if agent_id is not None:
            query = query.filter(AuditLog.agent_id == agent_id)
        if action is not None:
            query = query.filter(AuditLog.action == action)
        if entity_type is not None:
            query = query.filter(AuditLog.entity_type == entity_type)
        
        return query.order_by(desc(AuditLog.timestamp)).limit(limit).offset(offset).all()

    def get_count(
        self,
        agent_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> int:
        """Получить количество логов с фильтрацией."""
        query = self.db.query(AuditLog)
        
        if agent_id is not None:
            query = query.filter(AuditLog.agent_id == agent_id)
        if action is not None:
            query = query.filter(AuditLog.action == action)
        if entity_type is not None:
            query = query.filter(AuditLog.entity_type == entity_type)
        
        return query.count()
