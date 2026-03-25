-- Обновление поля action_type в таблице ticket_events
-- Изменяем тип с ENUM на VARCHAR(50) для поддержки новых значений

ALTER TABLE ticket_events 
MODIFY COLUMN action_type VARCHAR(50) NOT NULL;
