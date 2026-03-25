## Карта роутов (Jinja UI)

Ниже перечислены **фактически реализованные** маршруты в `app/web/jinja/routes/`.

### Структура модулей

```
app/web/jinja/routes/
├── main.py              # Главная страница, /home-page
├── auth.py              # Авторизация (login, logout, account)
├── utils.py             # Общие утилиты (фильтры, парсеры)
├── tickets/
│   ├── public.py        # Публичные роуты тикетов
│   └── admin.py         # Админские роуты тикетов
├── agents/
│   └── routes.py        # CRUD операторов
├── departments/
│   └── routes.py        # Список департаментов
└── lookups/
    ├── languages.py     # Языки
    └── categories.py    # Категории вопросов
```

---

### Публичные (без авторизации)

- **`GET /`**: начальный экран
- **`GET /new-ticket`**: форма создания тикета (+ первое сообщение + вложения)
- **`POST /new-ticket`**: создать тикет, затем показать трек-номер
- **`GET /get-ticket`**: форма ввода `track_id` для перехода к переписке
- **`POST /get-ticket`**: редирект на `/ticket/{track_id}/message`
- **`GET /ticket/{track_id}`**: универсальный роут:
  - без авторизации → редирект на `/ticket/{track_id}/message`
  - с авторизацией → редирект на `/tickets/{id}`
- **`GET /ticket/{track_id}/message`**: публичная переписка по тикету (только внешние сообщения)
- **`POST /ticket/{track_id}/message`**: отправить новое сообщение пользователем (проверка по email) + вложения

---

### Операторские (нужна авторизация)

#### Авторизация

- **`GET /login`**, **`POST /login`**: вход
- **`POST /logout`**: выход
- **`GET /accaunt`**: страница аккаунта

#### Навигация

- **`GET /home-page`**: редирект на `/operator/home-page`
- **`GET /operator/home-page`**: домашняя страница оператора

#### Тикеты (админские)

- **`GET /tickets`**: список тикетов
  - Параметры фильтрации:
    - `q` — поиск по track_id/subject/customer
    - `status_id`, `category_id`, `priority`
    - `archived` — `active` (по умолчанию), `archived`, `all`
    - `sort_by`, `sort_desc`, `limit`, `offset`
- **`GET /list-tickets`**: алиас → `/tickets`
- **`GET /tickets/{ticket_id}`**: карточка тикета + сообщения + события + вложения
- **`POST /tickets/{ticket_id}/reply`**: ответ оператора по тикету + вложения
  - Параметр `is_internal` для внутренних заметок
- **`POST /tickets/{ticket_id}/update`**: изменение параметров тикета
  - `status_id`, `priority`, `owner_id`, `category_id`
  - `is_locked`, `is_archived`
- **`POST /tickets/{ticket_id}/delete`**: удаление тикета (только неархивные)
- **`POST /tickets/{ticket_id}/restore`**: восстановление тикета из архива

#### Вложения

- **`GET /attachments/{attachment_id}/download`**: скачать вложение (только оператор)

#### Агенты (операторы)

- **`GET /agents`**: список операторов
  - Параметры: `search`, `role`, `department_id`, `sort_by`, `limit`, `offset`
- **`GET /agents/add`**: форма добавления агента
- **`POST /agents/add`**: создание агента
- **`GET /agents/{agent_id}/edit`**: форма редактирования агента
- **`POST /agents/{agent_id}/edit`**: обновление агента
- **`POST /agents/{agent_id}/delete`**: удаление агента
  - Защита: нельзя удалить самого себя

#### Департаменты

- **`GET /departments`**: список департаментов
- **`GET /department`**: алиас → `/departments`

#### Категории вопросов

- **`GET /question-category-list`**: список категорий
- **`GET /question-category-add`**: форма добавления (заглушка)
- **`GET /question-category-change`**: форма изменения (заглушка)

#### Языки

- **`GET /lookups/languages`**: список языков

---

## Изменения в последних версиях

### Версия от 2026-03-25

**Новые маршруты:**
- `POST /tickets/{ticket_id}/restore` — восстановление из архива

**Изменения:**
- Маршруты разделены по модулям (`tickets/`, `agents/`, `departments/`, `lookups/`)
- В `/tickets` добавлен фильтр `archived` (active/archived/all)
- Для архивных тикетов кнопка «Удалить» заменена на «Восстановить из архива»

**Технические изменения:**
- Поле `action_type` в `ticket_events` изменено с `ENUM` на `VARCHAR(50)`
- Добавлен тип события `unarchived` в `EventType`

