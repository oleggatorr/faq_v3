from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.ticket_read_state import TicketReadState
from app.models.message import Message
from app.models.ticket import Ticket


class TicketReadStateService:
    """
    Сервис для управления состоянием прочтения сообщений в тикетах.

    Отслеживает, какие сообщения были прочитаны владельцем тикета.
    """

    def __init__(self, session: Session):
        self.session = session

    def mark_as_read(self, *, ticket_id: int) -> None:
        """
        Отметить все сообщения в тикете как прочитанные.

        Обновляет last_read_message_id на максимальный ID сообщения в тикете.
        """
        print(f"[DEBUG Service] mark_as_read: ticket_id={ticket_id}")
        
        # Получаем максимальный ID сообщения в тикете
        max_message = self.session.query(Message).filter(
            Message.ticket_id == ticket_id
        ).order_by(Message.id.desc()).first()

        last_read_message_id = max_message.id if max_message else None
        print(f"[DEBUG Service] last_read_message_id={last_read_message_id}")

        # Обновляем или создаём запись о состоянии прочтения
        read_state = self.session.query(TicketReadState).filter(
            TicketReadState.ticket_id == ticket_id
        ).first()

        if read_state is None:
            print(f"[DEBUG Service] creating new read_state")
            read_state = TicketReadState(
                ticket_id=ticket_id,
                last_read_message_id=last_read_message_id,
                last_read_at=datetime.now(timezone.utc),
            )
            self.session.add(read_state)
        else:
            print(f"[DEBUG Service] updating existing read_state: old_last_read={read_state.last_read_message_id}")
            read_state.last_read_message_id = last_read_message_id
            read_state.last_read_at = datetime.now(timezone.utc)

        self.session.commit()  # ← Коммитим изменения в БД
        print(f"[DEBUG Service] commit done, read_state saved")

    def get_unread_count(self, *, ticket_id: int, exclude_internal: bool = True) -> int:
        """
        Получить количество непрочитанных сообщений в тикете.

        Args:
            ticket_id: ID тикета
            exclude_internal: Если True, не считать внутренние заметки
        """
        # Получаем last_read_message_id для тикета
        read_state = self.session.query(TicketReadState).filter(
            TicketReadState.ticket_id == ticket_id
        ).first()

        last_read_message_id = read_state.last_read_message_id if read_state else None

        # Считаем непрочитанные сообщения
        query = self.session.query(Message).filter(
            Message.ticket_id == ticket_id
        )

        if last_read_message_id is not None:
            query = query.filter(Message.id > last_read_message_id)

        if exclude_internal:
            query = query.filter(Message.is_internal == False)

        return query.count()

    def get_unread_counts_bulk(
        self,
        *,
        ticket_ids: list[int],
        exclude_internal: bool = True,
    ) -> dict[int, int]:
        """
        Получить количество непрочитанных сообщений для списка тикетов.

        Оптимизированная версия для массового получения счётчиков.

        Returns:
            dict[ticket_id, unread_count]
        """
        if not ticket_ids:
            return {}

        # Получаем все состояния прочтения для указанных тикетов
        read_states = self.session.query(TicketReadState).filter(
            TicketReadState.ticket_id.in_(ticket_ids)
        ).all()

        last_read_map = {rs.ticket_id: rs.last_read_message_id for rs in read_states}

        # Для тикетов без записи о прочтении считаем всё непрочитанным
        result = {}

        # Считаем сообщения для каждого тикета
        for ticket_id in ticket_ids:
            last_read_message_id = last_read_map.get(ticket_id)

            query = self.session.query(Message).filter(
                Message.ticket_id == ticket_id
            )

            if last_read_message_id is not None:
                query = query.filter(Message.id > last_read_message_id)

            if exclude_internal:
                query = query.filter(Message.is_internal == False)

            result[ticket_id] = query.count()

        return result

    def get_total_unread_for_agent(
        self,
        *,
        agent_id: int,
        exclude_internal: bool = True,
    ) -> int:
        """
        Получить общее количество непрочитанных сообщений по всем тикетам агента.

        Args:
            agent_id: ID агента (владельца тикетов)
            exclude_internal: Если True, не считать внутренние заметки

        Returns:
            Общее количество непрочитанных сообщений
        """
        # Получаем все тикеты агента
        tickets = self.session.query(Ticket.id).filter(
            Ticket.owner_id == agent_id
        ).all()

        if not tickets:
            return 0

        ticket_ids = [t[0] for t in tickets]

        # Получаем состояния прочтения
        read_states = self.session.query(TicketReadState).filter(
            TicketReadState.ticket_id.in_(ticket_ids)
        ).all()

        last_read_map = {rs.ticket_id: rs.last_read_message_id for rs in read_states}

        total_unread = 0

        # Для каждого тикета считаем непрочитанные
        for ticket_id in ticket_ids:
            last_read_message_id = last_read_map.get(ticket_id)

            query = self.session.query(func.count(Message.id)).filter(
                Message.ticket_id == ticket_id
            )

            if last_read_message_id is not None:
                query = query.filter(Message.id > last_read_message_id)

            if exclude_internal:
                query = query.filter(Message.is_internal == False)

            count = query.scalar() or 0
            total_unread += count

        return total_unread

    def get_tickets_with_unread(
        self,
        *,
        agent_id: int,
        exclude_internal: bool = True,
        min_unread: int = 1,
    ) -> list[dict]:
        """
        Получить список тикетов агента с непрочитанными сообщениями.

        Args:
            agent_id: ID агента (владельца тикетов)
            exclude_internal: Если True, не считать внутренние заметки
            min_unread: Минимальное количество непрочитанных для включения в список

        Returns:
            Список словарей: [{"ticket_id": int, "unread_count": int}, ...]
        """
        # Получаем все тикеты агента
        tickets = self.session.query(Ticket.id).filter(
            Ticket.owner_id == agent_id
        ).all()

        if not tickets:
            return []

        ticket_ids = [t[0] for t in tickets]

        # Получаем состояния прочтения
        read_states = self.session.query(TicketReadState).filter(
            TicketReadState.ticket_id.in_(ticket_ids)
        ).all()

        last_read_map = {rs.ticket_id: rs.last_read_message_id for rs in read_states}

        result = []

        # Для каждого тикета считаем непрочитанные
        for ticket_id in ticket_ids:
            last_read_message_id = last_read_map.get(ticket_id)

            query = self.session.query(func.count(Message.id)).filter(
                Message.ticket_id == ticket_id
            )

            if last_read_message_id is not None:
                query = query.filter(Message.id > last_read_message_id)

            if exclude_internal:
                query = query.filter(Message.is_internal == False)

            count = query.scalar() or 0

            if count >= min_unread:
                result.append({
                    "ticket_id": ticket_id,
                    "unread_count": count,
                })

        # Сортируем по количеству непрочитанных (убывание)
        result.sort(key=lambda x: -x["unread_count"])

        return result

    def reset_on_reassign(self, *, ticket_id: int) -> None:
        """
        Сбросить состояние прочтения при смене владельца тикета.

        Новый владелец должен увидеть все сообщения как непрочитанные.
        """
        read_state = self.session.query(TicketReadState).filter(
            TicketReadState.ticket_id == ticket_id
        ).first()

        if read_state is not None:
            self.session.delete(read_state)
            self.session.flush()
