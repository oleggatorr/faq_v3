-- Обновление названия статуса с "Ожидание ответа" на "Новая"
-- Статус ID 1: awaiting_reply -> Новая
UPDATE ticket_statuses 
SET name = 'Новая' 
WHERE code = 'awaiting_reply';
