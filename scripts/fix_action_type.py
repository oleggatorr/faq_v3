from sqlalchemy import create_engine, text

engine = create_engine('mysql+mysqlconnector://root:2xs_khHv0352@localhost/faq_db_v2')

with engine.connect() as conn:
    # Проверяем текущий тип
    result = conn.execute(text("""
        SELECT DATA_TYPE, COLUMN_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'faq_db_v2' 
          AND TABLE_NAME = 'ticket_events' 
          AND COLUMN_NAME = 'action_type'
    """))
    row = result.fetchone()
    print(f'Текущий тип: {row}')
    
    # Изменяем тип поля
    conn.execute(text('ALTER TABLE ticket_events MODIFY COLUMN action_type VARCHAR(50) NOT NULL'))
    print('Поле изменено на VARCHAR(50)')
    
    # Проверяем результат
    result = conn.execute(text("""
        SELECT DATA_TYPE, COLUMN_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'faq_db_v2' 
          AND TABLE_NAME = 'ticket_events' 
          AND COLUMN_NAME = 'action_type'
    """))
    row = result.fetchone()
    print(f'Новый тип: {row}')
    
    conn.commit()

print('Готово!')
