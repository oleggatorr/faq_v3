"""
Тесты для TicketReadStateService.

Проверка функционала отслеживания прочитанных сообщений в тикетах.
"""

import pytest
from sqlalchemy.orm import Session

from app.services.ticket.read_state_service import TicketReadStateService
from app.models.ticket_read_state import TicketReadState
from app.models.message import Message


class TestTicketReadStateService:
    """Тесты для TicketReadStateService."""

    def test_mark_as_read_creates_new_state(
        self, 
        db_session: Session, 
        test_ticket,
        test_messages,
    ):
        """mark_as_read создаёт новую запись о состоянии прочтения."""
        service = TicketReadStateService(db_session)
        
        # Отмечаем как прочитанное
        service.mark_as_read(ticket_id=test_ticket.id)
        
        # Проверяем, что запись создана
        read_state = db_session.query(TicketReadState).filter(
            TicketReadState.ticket_id == test_ticket.id
        ).first()
        
        assert read_state is not None
        assert read_state.ticket_id == test_ticket.id
        # Должен быть установлен ID последнего сообщения
        assert read_state.last_read_message_id is not None
        # Последнее прочитанное сообщение должно быть последним по ID
        assert read_state.last_read_message_id == max(m.id for m in test_messages)

    def test_mark_as_read_updates_existing_state(
        self, 
        db_session: Session, 
        test_ticket,
        test_messages,
    ):
        """mark_as_read обновляет существующую запись о состоянии."""
        from datetime import timezone
        
        service = TicketReadStateService(db_session)
        
        # Сначала отмечаем как прочитанное
        service.mark_as_read(ticket_id=test_ticket.id)
        first_state = db_session.query(TicketReadState).filter(
            TicketReadState.ticket_id == test_ticket.id
        ).first()
        first_read_at = first_state.last_read_at.replace(tzinfo=timezone.utc) if first_state.last_read_at.tzinfo is None else first_state.last_read_at
        
        # Добавляем новые сообщения
        new_message = Message(
            ticket_id=test_ticket.id,
            sender_name="John Doe",
            customer_email="john@example.com",
            body="New message after read",
            is_internal=False,
        )
        db_session.add(new_message)
        db_session.commit()
        
        # Снова отмечаем как прочитанное
        service.mark_as_read(ticket_id=test_ticket.id)
        
        # Проверяем обновление
        updated_state = db_session.query(TicketReadState).filter(
            TicketReadState.ticket_id == test_ticket.id
        ).first()
        
        assert updated_state.last_read_message_id == new_message.id
        updated_read_at = updated_state.last_read_at.replace(tzinfo=timezone.utc) if updated_state.last_read_at.tzinfo is None else updated_state.last_read_at
        assert updated_read_at >= first_read_at

    def test_get_unread_count_no_read_state(
        self, 
        db_session: Session, 
        test_ticket,
        test_messages,
    ):
        """get_unread_count возвращает все сообщения, если нет записи о прочтении."""
        service = TicketReadStateService(db_session)
        
        # Считаем непрочитанные (должны быть все, кроме внутренних)
        unread_count = service.get_unread_count(ticket_id=test_ticket.id)
        
        # В test_messages каждое 3-е сообщение внутреннее (i % 3 == 0)
        # i=0: internal, i=1: external, i=2: external, i=3: internal, i=4: external
        # Итого: 3 внешних сообщения
        expected_unread = sum(1 for m in test_messages if not m.is_internal)
        assert unread_count == expected_unread

    def test_get_unread_count_with_read_state(
        self, 
        db_session: Session, 
        test_ticket,
        test_messages,
    ):
        """get_unread_count правильно считает непрочитанные после отметки."""
        service = TicketReadStateService(db_session)
        
        # Отмечаем как прочитанное (все сообщения прочитаны)
        service.mark_as_read(ticket_id=test_ticket.id)
        
        # Добавляем новые сообщения
        new_message_1 = Message(
            ticket_id=test_ticket.id,
            sender_name="John Doe",
            customer_email="john@example.com",
            body="New message 1",
            is_internal=False,
        )
        new_message_2 = Message(
            ticket_id=test_ticket.id,
            sender_name="John Doe",
            customer_email="john@example.com",
            body="New message 2",
            is_internal=True,  # Внутреннее
        )
        db_session.add(new_message_1)
        db_session.add(new_message_2)
        db_session.commit()
        
        # Считаем непрочитанные
        unread_count = service.get_unread_count(ticket_id=test_ticket.id)
        
        # Должно быть 1 непрочитанное (новое внешнее сообщение)
        assert unread_count == 1

    def test_get_unread_count_exclude_internal(
        self, 
        db_session: Session, 
        test_ticket,
    ):
        """get_unread_count с exclude_internal=True не считает внутренние."""
        service = TicketReadStateService(db_session)
        
        # Создаём сообщения
        internal_msg = Message(
            ticket_id=test_ticket.id,
            sender_name="Agent",
            body="Internal note",
            is_internal=True,
        )
        external_msg = Message(
            ticket_id=test_ticket.id,
            sender_name="Customer",
            customer_email="customer@example.com",
            body="Customer message",
            is_internal=False,
        )
        db_session.add(internal_msg)
        db_session.add(external_msg)
        db_session.commit()
        
        # Считаем непрочитанные (исключая внутренние)
        unread_count = service.get_unread_count(
            ticket_id=test_ticket.id, 
            exclude_internal=True,
        )
        assert unread_count == 1
        
        # Считаем все непрочитанные
        unread_count_all = service.get_unread_count(
            ticket_id=test_ticket.id, 
            exclude_internal=False,
        )
        assert unread_count_all == 2

    def test_reset_on_reassign_removes_state(
        self, 
        db_session: Session, 
        test_ticket,
        test_messages,
    ):
        """reset_on_reassign удаляет запись о состоянии прочтения."""
        service = TicketReadStateService(db_session)
        
        # Сначала отмечаем как прочитанное
        service.mark_as_read(ticket_id=test_ticket.id)
        
        # Проверяем, что запись есть
        read_state = db_session.query(TicketReadState).filter(
            TicketReadState.ticket_id == test_ticket.id
        ).first()
        assert read_state is not None
        
        # Сбрасываем
        service.reset_on_reassign(ticket_id=test_ticket.id)
        
        # Проверяем, что запись удалена
        read_state = db_session.query(TicketReadState).filter(
            TicketReadState.ticket_id == test_ticket.id
        ).first()
        assert read_state is None

    def test_reset_on_reassign_no_state(
        self, 
        db_session: Session, 
        test_ticket,
    ):
        """reset_on_reassign не вызывает ошибок, если записи нет."""
        service = TicketReadStateService(db_session)
        
        # Вызываем на тикете без состояния
        service.reset_on_reassign(ticket_id=test_ticket.id)
        
        # Никаких ошибок, состояние остаётся отсутствующим
        read_state = db_session.query(TicketReadState).filter(
            TicketReadState.ticket_id == test_ticket.id
        ).first()
        assert read_state is None

    def test_get_unread_counts_bulk(
        self, 
        db_session: Session, 
        test_ticket,
        test_messages,
        service: TicketReadStateService,
    ):
        """get_unread_counts_bulk возвращает счётчики для списка тикетов."""
        # Отмечаем первый тикет как прочитанный
        service.mark_as_read(ticket_id=test_ticket.id)
        
        # Получаем счётчики
        counts = service.get_unread_counts_bulk(
            ticket_ids=[test_ticket.id],
            exclude_internal=True,
        )
        
        assert test_ticket.id in counts
        # Все сообщения прочитаны
        assert counts[test_ticket.id] == 0

    def test_get_unread_counts_bulk_empty_list(
        self, 
        service: TicketReadStateService,
    ):
        """get_unread_counts_bulk возвращает пустой dict для пустого списка."""
        counts = service.get_unread_counts_bulk(ticket_ids=[])
        assert counts == {}


@pytest.fixture
def service(db_session: Session) -> TicketReadStateService:
    """Фикстура сервиса для тестов."""
    return TicketReadStateService(db_session)
