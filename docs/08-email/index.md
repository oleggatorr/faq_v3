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
