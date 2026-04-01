-- Снятие уникального ограничения с поля email в таблице agents
-- Выполнить в MySQL

-- 1. Найти имя уникального индекса
SHOW INDEX FROM agents WHERE Key_name LIKE '%email%';

-- 2. Удалить уникальный индекс (замените ix_agents_email на фактическое имя)
ALTER TABLE agents DROP INDEX ix_agents_email;

-- 3. Создать обычный (неуникальный) индекс
CREATE INDEX ix_agents_email ON agents(email);

-- Проверка
SHOW INDEX FROM agents;
