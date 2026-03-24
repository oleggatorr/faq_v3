## Карта роутов (Jinja UI)

Ниже перечислены **фактически реализованные** маршруты в `app/web/jinja/routes.py`.

### Публичные (без авторизации)

- **`GET /`**: начальный экран
- **`GET /new-ticket`**: форма создания тикета (+ первое сообщение + вложения)
- **`POST /new-ticket`**: создать тикет, затем показать трек‑номер
- **`GET /get-ticket`**: форма ввода `track_id` для перехода к переписке
- **`POST /get-ticket`**: редирект на `/ticket/{track_id}/message`
- **`GET /ticket/{track_id}/message`**: публичная переписка по тикету (только внешние сообщения)
  - есть также алиас **`GET /ticket/{track_id}/messege`** (как в черновике)
- **`POST /ticket/{track_id}/message`**: отправить новое сообщение пользователем (проверка по email) + вложения

### Операторские (нужна авторизация)

- **`GET /login`**, **`POST /login`**: вход
- **`POST /logout`**: выход

- **`GET /home-page`**: редирект на `/tickets`
- **`GET /accaunt`**: заглушка страницы аккаунта (пока отображает `index.html`)

- **`GET /tickets`**: список тикетов
- **`GET /tickets/{ticket_id}`**: карточка тикета + сообщения + события + вложения
- **`POST /tickets/{ticket_id}/reply`**: ответ оператора по тикету + вложения
- **`GET /list-tickets`**: алиас → `/tickets`

- **`GET /ticket/{track_id}`**: алиас по `track_id` → редирект на `/tickets/{id}`
- **`GET /ticket/{track_id}/message`**: если оператор авторизован → редирект на `/tickets/{id}`

- **`GET /agents`**: список операторов
- **`GET /list-users`**: алиас → `/agents`
- **`GET /add-user`**: заглушка
- **`GET /change-user`**: заглушка

- **`GET /departments`**: список департаментов
- **`GET /department`**: алиас → `/departments`

- **`GET /question-category-list`**: список категорий вопросов
- **`GET /question-category-add`**: заглушка
- **`GET /question-category-change`**: заглушка

### Вложения

- **`GET /attachments/{attachment_id}/download`**: скачать вложение (только оператор)

