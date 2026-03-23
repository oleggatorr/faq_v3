from sqlalchemy import inspect

from models import Base
from models.base import engine


def create_tables_if_missing():
    """Create all tables declared in SQLAlchemy models."""
    Base.metadata.create_all(bind=engine)
    print("create_all executed: tables created if missing")

def test_connection(auto_create: bool = False):
    try:
        if auto_create:
            create_tables_if_missing()

        # Пытаемся подключиться
        connection = engine.connect()
        print("DB connection successful")
        
        # Получаем список таблиц
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Tables found: {len(tables)}")
        print(f"Tables: {', '.join(tables)}")
        
        # Проверяем наличие ключевых таблиц
        required_tables = ['agents', 'tickets', 'messages', 'departments', 'ticket_statuses']
        missing = [t for t in required_tables if t not in tables]
        
        if missing:
            print(f"Missing required tables: {missing}")
        else:
            print("All required tables found")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"Connection error: {e}")
        return False

if __name__ == "__main__":
    test_connection(auto_create=True)