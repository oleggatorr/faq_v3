from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agent import Agent, AgentRole
from app.models.question_category import QuestionCategory
from app.schemas.agent import AgentRead


@dataclass
class OperatorWithScore:
    """Оператор со score доступа к категории."""
    agent: AgentRead
    score: int
    has_explicit_access: bool
    is_admin: bool
    department_name: Optional[str] = None


class OperatorCategoryService:
    """
    Сервис для получения операторов с доступом к определённой категории.
    
    Логика доступа:
    1. Админы имеют доступ ко всем категориям (score = 100)
    2. Операторы с явным указанием категории в category_access (score = 10)
    3. Операторы без явного доступа к категории (score = 0)
    
    category_access хранится как строка с ID через запятую: "1,3,5"
    """

    def __init__(self, session: Session):
        self.session = session

    def get_operators_for_category(
        self,
        *,
        category_id: int,
        include_inactive: bool = False,
        only_auto_assign: bool = False,
        department_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[OperatorWithScore]:
        """
        Получить список операторов, которые могут работать с категорией.
        
        Args:
            category_id: ID категории
            include_inactive: Включая неактивных операторов
            only_auto_assign: Только операторы с включённым auto_assign
            department_id: Фильтр по департаменту (опционально)
            limit: Ограничение количества результатов
        
        Returns:
            Список OperatorWithScore, отсортированный по score (убывание)
        """
        query = self.session.query(Agent)
        
        # Фильтр по роли (только операторы и админы)
        query = query.filter(
            Agent.role.in_([AgentRole.operator, AgentRole.admin])
        )
        
        # Фильтр по активности
        if not include_inactive:
            query = query.filter(Agent.is_active == True)
        
        # Фильтр по auto_assign
        if only_auto_assign:
            query = query.filter(Agent.auto_assign == True)
        
        # Фильтр по департаменту
        if department_id is not None:
            query = query.filter(Agent.department_id == department_id)
        
        agents = query.all()
        
        result = []
        for agent in agents:
            # Определяем score и доступ
            is_admin = agent.role == AgentRole.admin
            has_explicit_access = self._has_category_access(
                agent.category_access, category_id
            )
            
            # Вычисляем score
            if is_admin:
                score = 100  # Админы всегда имеют максимальный приоритет
            elif has_explicit_access:
                score = 10  # Операторы с явным доступом
            else:
                score = 0  # Нет доступа
            
            # Получаем название департамента
            department_name = None
            if agent.department:
                department_name = agent.department.name
            
            operator_with_score = OperatorWithScore(
                agent=AgentRead.model_validate(agent),
                score=score,
                has_explicit_access=has_explicit_access,
                is_admin=is_admin,
                department_name=department_name,
            )
            result.append(operator_with_score)
        
        # Сортируем по score (убывание), затем по full_name
        result.sort(key=lambda x: (-x.score, x.agent.full_name))
        
        # Применяем limit
        if limit is not None:
            result = result[:limit]
        
        return result

    def get_best_operators_for_category(
        self,
        *,
        category_id: int,
        limit: int = 3,
        department_id: Optional[int] = None,
    ) -> list[OperatorWithScore]:
        """
        Получить лучших операторов для категории (с максимальным score).
        
        Args:
            category_id: ID категории
            limit: Количество операторов для возврата
            department_id: Фильтр по департаменту (опционально)
        
        Returns:
            Список лучших операторов
        """
        all_operators = self.get_operators_for_category(
            category_id=category_id,
            department_id=department_id,
            only_auto_assign=True,  # Только с включённым автоназначением
        )
        
        if not all_operators:
            return []
        
        # Находим максимальный score
        max_score = all_operators[0].score
        
        # Возвращаем операторов с максимальным score
        best_operators = [
            op for op in all_operators if op.score == max_score
        ][:limit]
        
        return best_operators

    def has_access_to_category(
        self,
        *,
        agent_id: int,
        category_id: int,
    ) -> bool:
        """
        Проверить, имеет ли оператор доступ к категории.
        
        Args:
            agent_id: ID оператора
            category_id: ID категории
        
        Returns:
            True если есть доступ
        """
        agent = self.session.query(Agent).filter(Agent.id == agent_id).first()
        if agent is None:
            return False
        
        # Админы имеют доступ всегда
        if agent.role == AgentRole.admin:
            return True
        
        return self._has_category_access(agent.category_access, category_id)

    def _has_category_access(
        self,
        category_access: str,
        category_id: int,
    ) -> bool:
        """
        Проверить, есть ли категория в списке доступа агента.
        
        category_access хранится как строка: "1,3,5" или ""
        
        Args:
            category_access: Строка с ID категорий через запятую
            category_id: ID проверяемой категории
        
        Returns:
            True если категория есть в списке
        """
        if not category_access:
            return False
        
        # Разбиваем строку и проверяем наличие
        category_ids = [
            int(id.strip()) 
            for id in category_access.split(',') 
            if id.strip()
        ]
        
        return category_id in category_ids

    def get_category_access_list(
        self,
        *,
        agent_id: int,
    ) -> list[int]:
        """
        Получить список ID категорий, доступных оператору.
        
        Args:
            agent_id: ID оператора
        
        Returns:
            Список ID категорий
        """
        agent = self.session.query(Agent).filter(Agent.id == agent_id).first()
        if agent is None:
            return []
        
        # Админы имеют доступ ко всем категориям
        if agent.role == AgentRole.admin:
            all_categories = self.session.query(QuestionCategory.id).all()
            return [cat[0] for cat in all_categories]
        
        if not agent.category_access:
            return []
        
        return [
            int(id.strip()) 
            for id in agent.category_access.split(',') 
            if id.strip()
        ]

    def add_category_access(
        self,
        *,
        agent_id: int,
        category_id: int,
        commit: bool = True,
    ) -> bool:
        """
        Добавить категорию в список доступа оператора.
        
        Args:
            agent_id: ID оператора
            category_id: ID категории
            commit: Закоммитить изменения
        
        Returns:
            True если категория была добавлена, False если уже существовала
        """
        agent = self.session.query(Agent).filter(Agent.id == agent_id).first()
        if agent is None:
            return False
        
        # Админам не нужно явно добавлять доступ
        if agent.role == AgentRole.admin:
            return True
        
        # Проверяем, есть ли уже категория
        if self._has_category_access(agent.category_access, category_id):
            return False
        
        # Добавляем категорию
        if agent.category_access:
            agent.category_access += f",{category_id}"
        else:
            agent.category_access = str(category_id)
        
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        
        return True

    def remove_category_access(
        self,
        *,
        agent_id: int,
        category_id: int,
        commit: bool = True,
    ) -> bool:
        """
        Удалить категорию из списка доступа оператора.
        
        Args:
            agent_id: ID оператора
            category_id: ID категории
            commit: Закоммитить изменения
        
        Returns:
            True если категория была удалена, False если не существовала
        """
        agent = self.session.query(Agent).filter(Agent.id == agent_id).first()
        if agent is None:
            return False
        
        # Админам не нужно удалять доступ
        if agent.role == AgentRole.admin:
            return False
        
        # Проверяем, есть ли категория
        if not self._has_category_access(agent.category_access, category_id):
            return False
        
        # Удаляем категорию из списка
        category_ids = [
            id.strip() 
            for id in agent.category_access.split(',') 
            if id.strip()
        ]
        category_ids = [
            id for id in category_ids 
            if id != str(category_id)
        ]
        
        agent.category_access = ",".join(category_ids)
        
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        
        return True
