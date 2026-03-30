"""
Тесты для OperatorCategoryService.

Проверка функционала получения операторов с доступом к категориям.
"""

import pytest
from sqlalchemy.orm import Session

from app.services.operator_category_service import (
    OperatorCategoryService,
    OperatorWithScore,
)
from app.models.agent import Agent, AgentRole
from app.models.question_category import QuestionCategory
from app.models.department import Department


class TestOperatorCategoryService:
    """Тесты для OperatorCategoryService."""

    def test_get_operators_for_category_admin_has_highest_score(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """Админ всегда имеет наивысший score (100)."""
        # Создаём админа и оператора с доступом
        admin = Agent(
            full_name="Test Admin User",
            email="test_admin@example.com",
            login="test_admin_user",
            password_hash="hashed",
            role=AgentRole.admin,
            is_active=True,
            category_access="",  # У админа пустой, но доступ есть
        )
        operator = Agent(
            full_name="Test Operator User",
            email="test_operator@example.com",
            login="test_operator_user",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access=str(test_category.id),  # Явный доступ
        )
        db_session.add(admin)
        db_session.add(operator)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        operators = service.get_operators_for_category(category_id=test_category.id)
        
        # Фильтруем только тестовых операторов (по full_name)
        test_operators = [
            op for op in operators 
            if op.agent.full_name.startswith("Test ")
        ]
        
        assert len(test_operators) == 2
        # Админ первый (score=100)
        assert test_operators[0].is_admin is True
        assert test_operators[0].score == 100
        # Оператор второй (score=10)
        assert test_operators[1].has_explicit_access is True
        assert test_operators[1].score == 10

    def test_get_operators_for_category_operator_with_access(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """Оператор с явным доступом имеет score=10."""
        operator = Agent(
            full_name="Test Op With Access",
            email="test_op_access@example.com",
            login="test_op_access",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access=f"{test_category.id}",
        )
        db_session.add(operator)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        operators = service.get_operators_for_category(category_id=test_category.id)
        
        # Фильтруем по префиксу
        test_operators = [
            op for op in operators 
            if op.agent.full_name.startswith("Test Op With Access")
        ]
        
        assert len(test_operators) == 1
        assert test_operators[0].has_explicit_access is True
        assert test_operators[0].score == 10
        assert test_operators[0].is_admin is False

    def test_get_operators_for_category_operator_without_access(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """Оператор без доступа имеет score=0."""
        operator = Agent(
            full_name="Test Op No Access",
            email="test_op_noaccess@example.com",
            login="test_op_noaccess",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access="999",  # Доступ к другой категории
        )
        db_session.add(operator)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        operators = service.get_operators_for_category(category_id=test_category.id)
        
        # Фильтруем по префиксу
        test_operators = [
            op for op in operators 
            if op.agent.full_name.startswith("Test Op No Access")
        ]
        
        assert len(test_operators) == 1
        assert test_operators[0].has_explicit_access is False
        assert test_operators[0].score == 0

    def test_get_operators_filters_inactive(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """Неактивные операторы исключаются по умолчанию."""
        active_op = Agent(
            full_name="Test Active Operator",
            email="test_active@example.com",
            login="test_active_op",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access=str(test_category.id),
        )
        inactive_op = Agent(
            full_name="Test Inactive Operator",
            email="test_inactive@example.com",
            login="test_inactive_op",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=False,
            category_access=str(test_category.id),
        )
        db_session.add(active_op)
        db_session.add(inactive_op)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        
        # По умолчанию только активные
        operators = service.get_operators_for_category(category_id=test_category.id)
        test_operators = [
            op for op in operators 
            if "Test " in op.agent.full_name
        ]
        assert len(test_operators) == 1
        assert test_operators[0].agent.full_name == "Test Active Operator"
        
        # С include_inactive=True - все
        operators_all = service.get_operators_for_category(
            category_id=test_category.id,
            include_inactive=True,
        )
        test_operators_all = [
            op for op in operators_all 
            if "Test " in op.agent.full_name
        ]
        assert len(test_operators_all) == 2

    def test_get_operators_filters_auto_assign(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """Фильтр только по операторам с auto_assign=True."""
        auto_assign_op = Agent(
            full_name="Test Auto Assign Op",
            email="test_auto@example.com",
            login="test_auto_assign_op",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            auto_assign=True,
            category_access=str(test_category.id),
        )
        no_auto_assign_op = Agent(
            full_name="Test No Auto Assign Op",
            email="test_noauto@example.com",
            login="test_no_auto_assign_op",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            auto_assign=False,
            category_access=str(test_category.id),
        )
        db_session.add(auto_assign_op)
        db_session.add(no_auto_assign_op)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        
        # Только с auto_assign=True
        operators = service.get_operators_for_category(
            category_id=test_category.id,
            only_auto_assign=True,
        )
        test_operators = [
            op for op in operators 
            if "Test " in op.agent.full_name
        ]
        assert len(test_operators) == 1
        assert test_operators[0].agent.auto_assign is True

    def test_get_operators_filters_by_department(
        self,
        db_session: Session,
        test_category: QuestionCategory,
        test_department,
    ):
        """Фильтр операторов по департаменту."""
        # Создаём второй департамент
        dept2 = Department(
            name=f"Test Dept 2",
            description="Test",
            is_active=True,
            sort_order=2,
        )
        db_session.add(dept2)
        db_session.commit()
        
        dept1_op = Agent(
            full_name="Test Dept1 Op",
            email="test_dept1@example.com",
            login="test_dept1_op",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            department_id=test_department.id,
            category_access=str(test_category.id),
        )
        dept2_op = Agent(
            full_name="Test Dept2 Op",
            email="test_dept2@example.com",
            login="test_dept2_op",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            department_id=dept2.id,
            category_access=str(test_category.id),
        )
        db_session.add(dept1_op)
        db_session.add(dept2_op)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        
        # Только из test_department
        operators = service.get_operators_for_category(
            category_id=test_category.id,
            department_id=test_department.id,
        )
        test_operators = [
            op for op in operators 
            if "Test Dept" in op.agent.full_name
        ]
        assert len(test_operators) == 1
        assert test_operators[0].agent.department_id == test_department.id

    def test_get_best_operators_for_category(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """get_best_operators возвращает операторов с максимальным score."""
        # Создаём операторов с разным score
        admin = Agent(
            full_name="Admin",
            email="admin2@example.com",
            login="admin2",
            password_hash="hashed",
            role=AgentRole.admin,
            is_active=True,
            auto_assign=True,
        )
        operator_with_access = Agent(
            full_name="Operator With Access",
            email="op_with@example.com",
            login="op_with",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            auto_assign=True,
            category_access=str(test_category.id),
        )
        operator_without_access = Agent(
            full_name="Operator Without Access",
            email="op_without@example.com",
            login="op_without",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            auto_assign=True,
            category_access="999",
        )
        db_session.add(admin)
        db_session.add(operator_with_access)
        db_session.add(operator_without_access)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        best = service.get_best_operators_for_category(
            category_id=test_category.id,
            limit=3,
        )
        
        # Все операторы с максимальным score (админы)
        assert len(best) >= 1
        assert all(op.score == 100 for op in best)

    def test_has_access_to_category(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """has_access_to_category проверяет доступ."""
        admin = Agent(
            full_name="Admin Access",
            email="admin3@example.com",
            login="admin3",
            password_hash="hashed",
            role=AgentRole.admin,
            is_active=True,
            category_access="",
        )
        operator_with = Agent(
            full_name="Operator With",
            email="op_with2@example.com",
            login="op_with2",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access=str(test_category.id),
        )
        operator_without = Agent(
            full_name="Operator Without",
            email="op_without2@example.com",
            login="op_without2",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access="999",
        )
        db_session.add(admin)
        db_session.add(operator_with)
        db_session.add(operator_without)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        
        # Админ имеет доступ
        assert service.has_access_to_category(
            agent_id=admin.id,
            category_id=test_category.id,
        ) is True
        
        # Оператор с доступом имеет
        assert service.has_access_to_category(
            agent_id=operator_with.id,
            category_id=test_category.id,
        ) is True
        
        # Оператор без доступа не имеет
        assert service.has_access_to_category(
            agent_id=operator_without.id,
            category_id=test_category.id,
        ) is False

    def test_get_category_access_list(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """get_category_access_list возвращает список ID категорий."""
        operator = Agent(
            full_name="Operator List",
            email="op_list@example.com",
            login="op_list",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access="1,2,3",
        )
        db_session.add(operator)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        access_list = service.get_category_access_list(agent_id=operator.id)
        
        assert access_list == [1, 2, 3]

    def test_add_category_access(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """add_category_access добавляет категорию в список."""
        operator = Agent(
            full_name="Operator Add",
            email="op_add@example.com",
            login="op_add",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access="1,2",
        )
        db_session.add(operator)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        
        # Добавляем категорию
        result = service.add_category_access(
            agent_id=operator.id,
            category_id=test_category.id,
        )
        
        assert result is True  # Была добавлена
        
        # Проверяем, что категория добавлена
        db_session.refresh(operator)
        access_list = service.get_category_access_list(agent_id=operator.id)
        assert test_category.id in access_list
        
        # Повторное добавление
        result2 = service.add_category_access(
            agent_id=operator.id,
            category_id=test_category.id,
        )
        assert result2 is False  # Уже существовала

    def test_remove_category_access(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """remove_category_access удаляет категорию из списка."""
        operator = Agent(
            full_name="Operator Remove",
            email="op_remove@example.com",
            login="op_remove",
            password_hash="hashed",
            role=AgentRole.operator,
            is_active=True,
            category_access="1,2,3",
        )
        db_session.add(operator)
        db_session.commit()
        
        service = OperatorCategoryService(db_session)
        
        # Удаляем категорию 2
        result = service.remove_category_access(
            agent_id=operator.id,
            category_id=2,
        )
        
        assert result is True  # Была удалена
        
        # Проверяем
        db_session.refresh(operator)
        access_list = service.get_category_access_list(agent_id=operator.id)
        assert 2 not in access_list
        assert access_list == [1, 3]
        
        # Повторное удаление
        result2 = service.remove_category_access(
            agent_id=operator.id,
            category_id=2,
        )
        assert result2 is False  # Уже не существовала

    def test_category_access_with_empty_string(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """_has_category_access корректно обрабатывает пустую строку."""
        service = OperatorCategoryService(db_session)
        
        # Пустая строка
        assert service._has_category_access("", test_category.id) is False
        
        # None
        assert service._has_category_access(None, test_category.id) is False

    def test_category_access_with_multiple_categories(
        self,
        db_session: Session,
        test_category: QuestionCategory,
    ):
        """_has_category_access работает со списком категорий."""
        service = OperatorCategoryService(db_session)
        
        # Список с несколькими категориями
        assert service._has_category_access("1,2,3", 2) is True
        assert service._has_category_access("1,2,3", 5) is False
        
        # Одна категория
        assert service._has_category_access("5", 5) is True
        assert service._has_category_access("5", 6) is False


@pytest.fixture
def test_category(db_session: Session) -> QuestionCategory:
    """Создаёт тестовую категорию."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    category = QuestionCategory(
        name=f"Test Category {unique_id}",
        description="Test",
        is_active=True,
        sort_order=1,
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category
