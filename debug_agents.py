from sqlalchemy import create_engine, text

DATABASE_URL = "mysql+pymysql://root:2xs_khHv0352@localhost/faq_db_v2?charset=utf8mb4"
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Все агенты
    print("=== ВСЕ АГЕНТЫ ===")
    agents = conn.execute(text("""
        SELECT id, full_name, role, is_active, auto_assign, category_access 
        FROM agents
    """)).fetchall()
    for a in agents:
        print(f"{a[0]}: {a[1]} | role={a[2]} | is_active={a[3]} | auto_assign={a[4]} | category_access='{a[5]}'")
    
    # Фильтр по роли
    print("\n=== ОПЕРАТОРЫ И АДМИНЫ ===")
    agents = conn.execute(text("""
        SELECT id, full_name, role, is_active, auto_assign 
        FROM agents
        WHERE role IN ('operator', 'admin')
    """)).fetchall()
    for a in agents:
        print(f"{a[0]}: {a[1]} | role={a[2]} | is_active={a[3]} | auto_assign={a[4]}")
    
    # Фильтр по роли + is_active
    print("\n=== АКТИВНЫЕ ОПЕРАТОРЫ И АДМИНЫ ===")
    agents = conn.execute(text("""
        SELECT id, full_name, role, is_active, auto_assign 
        FROM agents
        WHERE role IN ('operator', 'admin') AND is_active = 1
    """)).fetchall()
    for a in agents:
        print(f"{a[0]}: {a[1]} | role={a[2]} | is_active={a[3]} | auto_assign={a[4]}")
    
    # Фильтр по роли + is_active + auto_assign
    print("\n=== АКТИВНЫЕ ОПЕРАТОРЫ С auto_assign=1 ===")
    agents = conn.execute(text("""
        SELECT id, full_name, role, is_active, auto_assign, category_access 
        FROM agents
        WHERE role IN ('operator', 'admin') AND is_active = 1 AND auto_assign = 1
    """)).fetchall()
    for a in agents:
        print(f"{a[0]}: {a[1]} | role={a[2]} | auto_assign={a[4]} | category_access='{a[5]}'")
