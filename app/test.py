from sqlalchemy import create_engine, inspect
from models.base import SQLALCHEMY_DATABASE_URL, engine

def test_connection():
    try:
        # Пытаемся подключиться
        connection = engine.connect()
        print("✅ Подключение к БД успешно!")
        
        # Получаем список таблиц
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📊 Найдено таблиц: {len(tables)}")
        print(f"Таблицы: {', '.join(tables)}")
        
        # Проверяем наличие ключевых таблиц
        required_tables = ['agents', 'tickets', 'messages', 'departments', 'ticket_statuses']
        missing = [t for t in required_tables if t not in tables]
        
        if missing:
            print(f"❌ Отсутствуют таблицы: {missing}")
        else:
            print("✅ Все основные таблицы найдены")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    test_connection()