from sqlalchemy import create_engine, update, text
from app.models.base import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB
from app.models.agent import Agent

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}?charset=utf8mb4"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Обновляем всех операторов
    result = conn.execute(
        update(Agent).where(Agent.auto_assign == False).values(auto_assign=True)
    )
    conn.commit()
    print(f"Обновлено операторов: {result.rowcount}")
    
    # Проверяем
    agents = conn.execute(
        text("SELECT id, full_name, auto_assign FROM agents LIMIT 5")
    ).fetchall()
    for a in agents:
        print(f"{a[0]}: {a[1]} | auto_assign={a[2]}")
