from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.services.operator_category_service import OperatorCategoryService, OperatorWithScore


class AssignmentService:
    """
    Сервис автоназначения тикетов на операторов.
    
    Использует OperatorCategoryService для получения списка операторов,
    имеющих доступ к определённой категории вопросов.
    """

    def __init__(self, session: Session):
        self.session = session
        self.operator_category_service = OperatorCategoryService(session)

    def get_available_operators(
        self,
        *,
        category_id: int,
        department_id: Optional[int] = None,
        only_auto_assign: bool = True,
        include_inactive: bool = False,
        limit: Optional[int] = None,
        random: bool = False,
    ) -> list[OperatorWithScore]:
        """
        Получить список операторов, доступных для назначения на тикет.

        Args:
            category_id: ID категории вопроса (из тикета)
            department_id: ID департамента (опционально, для фильтрации)
            only_auto_assign: Только операторы с включённым auto_assign
            include_inactive: Включая неактивных операторов
            limit: Ограничение количества результатов
            random: Перемешать операторов (для случайного выбора)

        Returns:
            Список операторов со score, отсортированный по убыванию score
        """
        return self.operator_category_service.get_operators_for_category(
            category_id=category_id,
            include_inactive=include_inactive,
            only_auto_assign=only_auto_assign,
            department_id=department_id,
            limit=limit,
            random=random,
        )

    def get_best_operators(
        self,
        *,
        category_id: int,
        department_id: Optional[int] = None,
        limit: int = 3,
    ) -> list[OperatorWithScore]:
        """
        Получить лучших операторов для назначения на тикет.
        
        Возвращает операторов с максимальным score (админы или операторы с доступом к категории).
        
        Args:
            category_id: ID категории вопроса (из тикета)
            department_id: ID департамента (опционально)
            limit: Количество операторов для возврата (по умолчанию 3)
        
        Returns:
            Список лучших операторов
        """
        return self.operator_category_service.get_best_operators_for_category(
            category_id=category_id,
            department_id=department_id,
            limit=limit,
        )

    def auto_assign(
        self,
        *,
        ticket_id: int,
        strategy: str = "round_robin",
    ) -> int | None:
        """
        Автоматически назначить оператора на тикет.
        
        Args:
            ticket_id: ID тикета
            strategy: Стратегия выбора оператора:
                - "round_robin" — по очереди
                - "load_balanced" — по наименьшей нагрузке
                - "best_match" — оператор с максимальным score
        
        Returns:
            ID назначенного оператора или None, если не удалось назначить
        
        TODO: Реализовать стратегии выбора
        """
        # Получаем тикет
        from app.models.ticket import Ticket
        ticket = self.session.query(Ticket).filter(Ticket.id == ticket_id).first()
        if ticket is None:
            return None
        
        # Получаем доступных операторов
        operators = self.get_available_operators(
            category_id=ticket.category_id,
            department_id=ticket.department_id,
            only_auto_assign=True,
            include_inactive=False,
        )
        
        if not operators:
            return None
        
        # Пока используем простую стратегию — первый оператор с максимальным score
        # TODO: Реализовать полноценные стратегии
        best_operator = operators[0]
        
        return best_operator.agent.id
