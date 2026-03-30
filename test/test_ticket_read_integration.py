"""
Интеграционные тесты для TicketService с TicketReadStateService.

Проверка интеграции счётчика непрочитанных сообщений в TicketService.
"""

import pytest
from sqlalchemy.orm import Session

from app.services.ticket.ticket_service import TicketService
from app.services.ticket.ticket_event_service import TicketEventService
from app.services.ticket.read_state_service import TicketReadStateService
from app.models.message import Message
from app.schemas.message import MessageCreate


class TestTicketServiceIntegration:
    """Тесты интеграции TicketService с read state."""

    def test_assign_owner_resets_read_state(
        self,
        db_session: Session,
        test_ticket,
        test_messages,
        test_agent2,
    ):
        """assign_owner сбрасывает состояние прочтения при смене владельца."""
        from app.models.ticket_read_state import TicketReadState
        
        # Создаём сервис только с read_state_service (без event_service для SQLite)
        ticket_service = TicketService(
            db_session,
            ticket_read_state_service=TicketReadStateService(db_session),
        )
        
        # Сначала отмечаем как прочитанное
        ticket_service.mark_as_read(ticket_id=test_ticket.id)
        
        # Проверяем, что состояние есть
        read_state = db_session.query(TicketReadState).filter(
            TicketReadState.ticket_id == test_ticket.id
        ).first()
        assert read_state is not None
        
        # Сменяем владельца
        ticket_service.assign_owner(
            ticket_id=test_ticket.id,
            new_owner_id=test_agent2.id,
            agent_id=test_agent2.id,
        )
        
        # Проверяем, что состояние сброшено
        read_state = db_session.query(TicketReadState).filter(
            TicketReadState.ticket_id == test_ticket.id
        ).first()
        # Состояние должно быть удалено
        assert read_state is None

    def test_get_unread_count_via_ticket_service(
        self,
        db_session: Session,
        test_ticket,
        test_messages,
    ):
        """get_unread_count работает через TicketService."""
        ticket_service = TicketService(
            db_session,
            ticket_event_service=TicketEventService(db_session),
            ticket_read_state_service=TicketReadStateService(db_session),
        )
        
        # Получаем количество непрочитанных (должны быть все внешние сообщения)
        unread_count = ticket_service.get_unread_count(ticket_id=test_ticket.id)
        
        # В test_messages каждое 3-е сообщение внутреннее (i % 3 == 0)
        # i=0: internal, i=1: external, i=2: external, i=3: internal, i=4: external
        # Итого: 3 внешних сообщения
        expected_unread = sum(1 for m in test_messages if not m.is_internal)
        assert unread_count == expected_unread

    def test_mark_as_read_via_ticket_service(
        self,
        db_session: Session,
        test_ticket,
        test_messages,
    ):
        """mark_as_read работает через TicketService."""
        ticket_service = TicketService(
            db_session,
            ticket_event_service=TicketEventService(db_session),
            ticket_read_state_service=TicketReadStateService(db_session),
        )
        
        # Отмечаем как прочитанное
        ticket_service.mark_as_read(ticket_id=test_ticket.id)
        
        # Проверяем, что непрочитанных нет
        unread_count = ticket_service.get_unread_count(ticket_id=test_ticket.id)
        assert unread_count == 0

    def test_list_with_unread_count(
        self,
        db_session: Session,
        test_ticket,
        test_messages,
        test_agent,
    ):
        """list возвращает unread_count при include_unread=True."""
        ticket_service = TicketService(
            db_session,
            ticket_event_service=TicketEventService(db_session),
            ticket_read_state_service=TicketReadStateService(db_session),
        )
        
        # Получаем список с unread_count
        tickets = ticket_service.list(
            include_unread=True,
            agent_id=test_agent.id,
        )
        
        assert len(tickets) > 0
        ticket = next((t for t in tickets if t.id == test_ticket.id), None)
        assert ticket is not None
        assert ticket.unread_count is not None
        # Должны быть только внешние сообщения
        expected_unread = sum(1 for m in test_messages if not m.is_internal)
        assert ticket.unread_count == expected_unread

    def test_list_without_unread_count(
        self,
        db_session: Session,
        test_ticket,
        test_messages,
    ):
        """list не возвращает unread_count по умолчанию."""
        ticket_service = TicketService(
            db_session,
            ticket_event_service=TicketEventService(db_session),
            ticket_read_state_service=TicketReadStateService(db_session),
        )
        
        # Получаем список без unread_count
        tickets = ticket_service.list()
        
        ticket = next((t for t in tickets if t.id == test_ticket.id), None)
        assert ticket is not None
        # unread_count может быть None (не вычислялся)
        assert ticket.unread_count is None
