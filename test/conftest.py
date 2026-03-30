import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv

from app.models.base import Base
from app.models.agent import Agent, AgentRole
from app.models.ticket import Ticket, Priority
from app.models.message import Message
from app.models.ticket_read_state import TicketReadState
from app.models.department import Department
from app.models.ticket_status import TicketStatus
from app.services.ticket.read_state_service import TicketReadStateService

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем настройки подключения из .env
MYSQL_USER = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "password")
MYSQL_HOST = os.getenv("DB_HOST", "localhost")
MYSQL_DB = os.getenv("DB_NAME", "faq_db_v2")

# Для тестов можно использовать отдельную БД
# Если есть тестовая БД, установите TEST_DB_NAME в .env
TEST_DB_NAME = os.getenv("TEST_DB_NAME", MYSQL_DB)

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{TEST_DB_NAME}?charset=utf8mb4"


@pytest.fixture(scope="session")
def engine():
    """
    Создаёт движок для подключения к реальной БД.
    
    Используется session scope, чтобы не пересоздавать движок для каждого теста.
    """
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Проверка подключения перед использованием
        echo=False,
    )


@pytest.fixture
def db_session(engine):
    """
    Создаёт сессию БД для каждого теста с откатом транзакции.
    
    Каждый тест работает в изолированной транзакции, которая откатывается
    после завершения теста. Это гарантирует чистоту данных между тестами.
    """
    # Создаём таблицы, если их нет
    Base.metadata.create_all(bind=engine)
    
    # Подключаемся и начинаем транзакцию
    connection = engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
    )
    session = SessionLocal()
    
    try:
        yield session
    finally:
        # Откатываем все изменения после теста
        transaction.rollback()
        session.close()
        connection.close()


@pytest.fixture
def test_agent(db_session: Session) -> Agent:
    """Создаёт тестового агента."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    agent = Agent(
        full_name="Test Agent",
        email=f"test_{unique_id}@example.com",
        login=f"test_agent_{unique_id}",
        password_hash="hashed_password",
        role=AgentRole.operator,
        is_active=True,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def test_agent2(db_session: Session) -> Agent:
    """Создаёт второго тестового агента."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    agent = Agent(
        full_name="Test Agent 2",
        email=f"test2_{unique_id}@example.com",
        login=f"test_agent2_{unique_id}",
        password_hash="hashed_password",
        role=AgentRole.operator,
        is_active=True,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def test_department(db_session: Session) -> Department:
    """Создаёт тестовый департамент."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    dept = Department(
        name=f"Test Department {unique_id}",
        description="Test",
        is_active=True,
        sort_order=1,
    )
    db_session.add(dept)
    db_session.commit()
    db_session.refresh(dept)
    return dept


@pytest.fixture
def test_status(db_session: Session) -> TicketStatus:
    """Создаёт тестовый статус."""
    # Проверяем, есть ли уже статусы в БД
    status = db_session.query(TicketStatus).filter(TicketStatus.code == "test_new").first()
    if status is None:
        status = TicketStatus(
            code="test_new",
            name="Test New",
            is_closed=False,
            is_default=False,
            sort_order=100,
        )
        db_session.add(status)
        db_session.commit()
        db_session.refresh(status)
    return status


@pytest.fixture
def test_ticket(
    db_session: Session, 
    test_department: Department, 
    test_status: TicketStatus,
    test_agent: Agent,
) -> Ticket:
    """Создаёт тестовый тикет."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    
    ticket = Ticket(
        track_id=f"TEST-{unique_id}",
        customer_name="John Doe",
        customer_email="john@example.com",
        customer_ip="127.0.0.1",
        department_id=test_department.id,
        status_id=test_status.id,
        priority=Priority.normal,
        subject="Test Ticket",
        preview_message="Test preview",
        owner_id=test_agent.id,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


@pytest.fixture
def test_messages(db_session: Session, test_ticket: Ticket) -> list[Message]:
    """Создаёт набор тестовых сообщений."""
    messages = []
    for i in range(5):
        msg = Message(
            ticket_id=test_ticket.id,
            sender_name="John Doe" if i % 2 == 0 else None,
            customer_email="john@example.com" if i % 2 == 0 else None,
            body=f"Test message {i + 1}",
            is_internal=(i % 3 == 0),  # Каждое 3-е сообщение внутреннее
        )
        db_session.add(msg)
        messages.append(msg)
    
    db_session.commit()
    
    # Обновляем ID в объектах
    for msg in messages:
        db_session.refresh(msg)
    
    return messages


@pytest.fixture
def service(db_session: Session) -> TicketReadStateService:
    """Фикстура сервиса для тестов."""
    return TicketReadStateService(db_session)
