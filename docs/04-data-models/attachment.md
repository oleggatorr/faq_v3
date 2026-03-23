# Модель Attachment

## Назначение

`Attachment` описывает файл, прикрепленный к сообщению в тикете.

Файл модели: `app/models/attachment.py`.

## Таблица

- Таблица: `attachments`
- Первичный ключ: `id`

## Поля

### Идентификация и связь

- `id` (`Integer`, PK, autoincrement)
- `message_id` (`Integer`, FK -> `messages.id`, `nullable=False`, `index=True`)

### Файловые атрибуты

- `original_filename` (`String(255)`, `nullable=False`) - исходное имя файла.
- `stored_filename` (`String(100)`, `nullable=False`, `index=True`) - имя в хранилище.
- `file_path` (`String(500)`, `nullable=False`) - путь к файлу в storage.
- `file_size` (`Integer`, `nullable=False`) - размер в байтах.
- `mime_type` (`String(100)`, `nullable=False`) - MIME тип.
- `file_hash` (`String(64)`, `nullable=True`, `index=True`) - хеш содержимого.

### Аудит загрузки

- `uploaded_by_agent_id` (`BigInteger`, FK -> `agents.id`, `nullable=True`, `index=True`)
- `uploaded_at` (`DateTime`, server default `now()`)
- `download_count` (`Integer`, default `0`, `nullable=False`)

## Связи

- `message` -> `Message`
- `uploader` -> `Agent`

## Бизнес-правила

- Вложение принадлежит конкретному сообщению.
- При удалении сообщения вложения должны удаляться каскадно.
- Для публичного клиента доступ к скачиванию должен проходить через проверку доступа к тикету.
- `download_count` обновляется при успешной выдаче файла.

## Примеры

### Файл от пользователя

- `uploaded_by_agent_id`: `null`
- `original_filename`: `photo.jpg`
- `mime_type`: `image/jpeg`

### Файл от оператора

- `uploaded_by_agent_id`: `8`
- `original_filename`: `report.pdf`
- `mime_type`: `application/pdf`

## Риски и рекомендации

- `file_path` должен быть нормализован и проверен на traversal-атаки.
- Проверки MIME и расширения лучше делать и на API-уровне, и на уровне сервиса.
- Для дубликатов полезно использовать `file_hash` + размер файла.
