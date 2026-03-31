# Email-уведомления

## Сервис `app/services/email_service.py`

### Функция `send_email(to, subject, body)`

Базовая функция отправки. **Временная заглушка**: фактическая доставка на `olegfesenko365@gmail.com` (отправитель и получатель).

### События и получатели

| Событие | Получатель | Вызов |
|---------|------------|-------|
| Создание тикета | Почта департамента | `notify_ticket_created` в роуте `/new-ticket` |
| Новое сообщение | Назначенный оператор (owner) или департамент | `notify_new_message` в роуте `/tickets/{id}/reply` |
| Изменение статуса | Заявитель (customer_email) | `notify_status_changed` в `TicketService.change_status` |

### Заглушка

- `STUB_FROM` = `olegfesenko365@gmail.com`
- `STUB_TO` = `olegfesenko365@gmail.com`
- Реальный `to` сохраняется в лог для отладки.

### Подключение реальной отправки

Заменить заглушку в `send_email()` на вызов SMTP (smtplib, aiosmtplib и т.п.).

---

## Баны (Email и IP)

### Модели

- `app/models/ban.py` — модели `BannedEmail` и `BannedIP`
- `app/services/ban_service.py` — сервис для управления банами
- `app/services/utils.py` — утилиты `ip_to_int()`, `int_to_ip()`, `ip_in_range()`

### Таблицы БД

**`banned_emails`** — забаненные email-адреса:
- `id` — первичный ключ
- `email` — email (уникальный, индекс)
- `banned_by` — кто забанил (FK на agents.id)
- `reason` — причина (опционально)
- `created_at` — дата бана

**`banned_ips`** — забаненные IP (диапазоны):
- `id` — первичный ключ
- `ip_from` — начало диапазона (BIGINT)
- `ip_to` — конец диапазона (BIGINT)
- `ip_display` — человекочитаемое представление (напр. "192.168.1.*")
- `banned_by` — кто забанил (FK на agents.id)
- `created_at` — дата бана

### API

**`GET /api/bans/emails`** — список забаненных email  
**`POST /api/bans/emails`** — добавить email в бан-лист  
**`DELETE /api/bans/emails/{ban_id}`** — удалить бан по email

**`GET /api/bans/ips`** — список забаненных IP  
**`POST /api/bans/ips`** — добавить IP или диапазон  
**`DELETE /api/bans/ips/{ban_id}`** — удалить бан по IP

**`GET /api/bans/check?email=...&ip=...`** — проверить, забанены ли email/IP

### Интеграция

Проверка банов встроена в роут создания тикета (`POST /new-ticket`):
- Если email забанен → возврат 403 с ошибкой
- Если IP забанен → возврат 403 с ошибкой
