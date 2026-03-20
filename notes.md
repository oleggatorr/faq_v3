Функции сервисного слоя (Service Layer)
1. AgentService - сервис управления агентами
text
- register_agent() - регистрация нового агента с хешированием пароля
- authenticate_agent() - аутентификация по email и паролю, выдача токена
- get_agent_by_id() - получение агента с загрузкой связанных данных
- update_agent_profile() - обновление профиля с проверкой прав
- change_password() - смена пароля с проверкой текущего
- reset_password() - сброс пароля через email
- update_last_login() - обновление времени последнего входа
- get_agents_by_department() - получение агентов отдела
- get_available_agents() - получение свободных агентов для назначения
- deactivate_agent() - деактивация агента с перераспределением тикетов
- get_agent_statistics() - статистика работы агента (тикеты, время ответа)
- check_permissions() - проверка прав доступа к ресурсу
- update_avatar() - обновление аватара с загрузкой файла
- get_agent_activity_log() - получение лога действий агента
2. TicketService - сервис управления тикетами
text
- create_ticket_with_message() - создание тикета и первого сообщения (транзакция)
- get_ticket_by_id() - получение тикета с полной информацией
- get_ticket_by_track_id() - получение по публичному ID
- update_ticket() - обновление данных тикета с валидацией
- assign_ticket() - назначение агента с созданием события
- unassign_ticket() - снятие назначения
- change_ticket_status() - изменение статуса с валидацией перехода
- change_ticket_priority() - изменение приоритета с уведомлением
- change_ticket_category() - изменение категории
- change_ticket_department() - изменение отдела с перераспределением
- lock_ticket() - блокировка тикета (только для админов)
- unlock_ticket() - разблокировка
- archive_ticket() - архивирование тикета
- restore_ticket() - восстановление из архива
- merge_tickets() - объединение нескольких тикетов в один
- split_ticket() - разделение тикета на несколько
- add_message_to_ticket() - добавление сообщения с обновлением счетчиков
- add_internal_note() - добавление внутренней заметки
- get_ticket_timeline() - получение хронологии событий
- get_ticket_messages() - получение сообщений с пагинацией
- get_ticket_by_filters() - поиск тикетов с фильтрацией
- get_ticket_statistics() - статистика по тикетам
- calculate_response_time() - расчет времени первого ответа
- calculate_resolution_time() - расчет времени закрытия
- check_sla_compliance() - проверка соблюдения SLA
- escalate_ticket() - эскалация тикета при нарушении SLA
- get_tickets_for_agent() - получение тикетов назначенных агенту
- get_unassigned_tickets() - получение неназначенных тикетов
- auto_assign_ticket() - автоматическое назначение по round-robin
- bulk_update_tickets() - массовое обновление статусов/приоритетов
- bulk_assign_tickets() - массовое назначение агентов
- export_tickets() - экспорт тикетов в различные форматы
- import_tickets() - импорт тикетов из внешних систем
- generate_track_id() - генерация уникального публичного ID
- validate_ticket_transition() - проверка возможности перехода
- get_ticket_history() - получение полной истории изменений
3. MessageService - сервис управления сообщениями
text
- create_message() - создание сообщения с обновлением тикета
- get_message_by_id() - получение сообщения с вложениями
- update_message() - редактирование сообщения (ограничение по времени)
- delete_message() - удаление сообщения (soft delete или hard)
- reply_to_message() - ответ на сообщение с цитированием
- get_ticket_messages() - получение всех сообщений тикета
- get_internal_messages() - получение внутренних заметок
- get_public_messages() - получение публичных сообщений
- mark_message_as_read() - отметка о прочтении агентом
- get_unread_messages() - получение непрочитанных сообщений
- send_email_notification() - отправка уведомления на email
- send_push_notification() - отправка push-уведомления
- format_message_for_email() - форматирование для email-рассылки
- sanitize_message_html() - очистка HTML от опасных тегов
- extract_mentions() - извлечение упоминаний @username
- check_for_spam() - проверка сообщения на спам
- translate_message() - автоматический перевод сообщения
- add_message_template() - сохранение шаблона сообщения
- get_message_templates() - получение шаблонов сообщений
- apply_template() - применение шаблона с подстановкой переменных
- get_message_statistics() - статистика по сообщениям
- search_messages() - полнотекстовый поиск по сообщениям
- export_messages() - экспорт сообщений тикета
- import_messages() - импорт сообщений из внешних источников
4. AttachmentService - сервис управления вложениями
text
- upload_attachment() - загрузка файла с проверкой размера и типа
- get_attachment_by_id() - получение информации о вложении
- download_attachment() - скачивание файла с увеличением счетчика
- delete_attachment() - удаление файла и записи
- get_attachments_by_message() - получение вложений сообщения
- get_attachments_by_ticket() - получение всех вложений тикета
- bulk_upload_attachments() - массовая загрузка файлов
- check_duplicate_file() - проверка дубликатов по хешу
- generate_thumbnail() - генерация превью для изображений
- scan_for_virus() - сканирование файла на вирусы
- validate_file_type() - проверка разрешенного типа файла
- validate_file_size() - проверка размера файла
- get_storage_usage() - статистика использования хранилища
- cleanup_orphaned_attachments() - очистка потерянных вложений
- get_attachment_statistics() - статистика по вложениям
- compress_image() - сжатие изображений
- rotate_image() - поворот изображения
- get_file_hash() - вычисление хеша файла
- store_file() - сохранение файла в хранилище
- delete_from_storage() - удаление из физического хранилища
- migrate_attachments() - миграция между хранилищами
5. DepartmentService - сервис управления отделами
text
- create_department() - создание отдела
- update_department() - обновление информации отдела
- delete_department() - удаление с проверкой зависимостей
- get_department_by_id() - получение отдела
- get_all_departments() - получение всех отделов
- get_department_hierarchy() - получение иерархической структуры
- get_department_tree() - получение дерева отделов
- reorder_departments() - переупорядочивание отделов
- move_department() - перемещение отдела в иерархии
- assign_head_agent() - назначение руководителя отдела
- get_department_agents() - получение агентов отдела
- get_department_statistics() - статистика по отделу
- get_department_tickets() - получение тикетов отдела
- transfer_agents() - массовое перемещение агентов между отделами
- get_available_departments() - получение доступных отделов
- validate_department_email() - проверка уникальности email
- export_departments() - экспорт отделов
- import_departments() - импорт отделов
- calculate_workload() - расчет нагрузки на отдел
6. CategoryService - сервис управления категориями
text
- create_category() - создание категории
- update_category() - обновление категории
- delete_category() - удаление с перемещением тикетов
- get_category_by_id() - получение категории
- get_category_tree() - получение дерева категорий
- get_category_path() - получение пути категории
- move_category() - перемещение категории
- reorder_categories() - переупорядочивание категорий
- get_categories_by_department() - получение категорий отдела
- get_categories_with_stats() - категории со статистикой
- get_popular_categories() - популярные категории
- search_categories() - поиск категорий
- validate_category_name() - проверка уникальности имени
- get_category_analytics() - аналитика по категории
- get_subcategories() - получение подкатегорий
- build_category_breadcrumbs() - построение хлебных крошек
- export_categories() - экспорт категорий
- import_categories() - импорт категорий
7. StatusService - сервис управления статусами
text
- create_status() - создание статуса
- update_status() - обновление статуса
- delete_status() - удаление с проверкой использования
- get_status_by_id() - получение статуса
- get_all_statuses() - получение всех статусов
- get_default_status() - получение статуса по умолчанию
- set_default_status() - установка статуса по умолчанию
- get_status_workflow() - получение workflow статусов
- validate_transition() - проверка разрешенности перехода
- get_next_statuses() - получение возможных следующих статусов
- get_status_statistics() - статистика по статусам
- get_status_by_category() - получение статусов по категории
- get_status_flow() - получение графа переходов
- auto_transition_statuses() - автоматический переход по таймауту
- bulk_update_statuses() - массовое обновление статусов
- get_status_history() - история изменений статуса
- validate_closed_status() - проверка закрывающих статусов
8. LanguageService - сервис управления языками
text
- create_language() - создание языка
- update_language() - обновление языка
- delete_language() - удаление языка
- get_language_by_id() - получение языка
- get_language_by_code() - получение по коду
- get_active_languages() - получение активных языков
- get_default_language() - получение языка по умолчанию
- set_default_language() - установка языка по умолчанию
- get_language_statistics() - статистика использования языков
- get_translations() - получение переводов
- add_translation() - добавление перевода
- update_translation() - обновление перевода
- delete_translation() - удаление перевода
- export_translations() - экспорт переводов
- import_translations() - импорт переводов
- detect_missing_translations() - обнаружение недостающих переводов
- get_language_pack() - получение пакета переводов
- validate_locale() - валидация локали
- get_rtl_languages() - получение языков с RTL
9. EventService - сервис управления событиями
text
- create_event() - создание события
- get_event_by_id() - получение события
- get_ticket_events() - получение событий тикета
- get_agent_events() - получение событий агента
- get_events_by_type() - получение по типу
- get_events_timeline() - получение временной линии
- format_event_message() - форматирование сообщения события
- get_event_statistics() - статистика событий
- calculate_response_metrics() - расчет метрик ответа
- calculate_resolution_metrics() - расчет метрик закрытия
- get_agent_performance() - производительность агентов
- get_sla_breaches() - получение нарушений SLA
- export_events() - экспорт событий
- cleanup_old_events() - очистка старых событий
- get_event_graph() - построение графа событий
- detect_anomalies() - обнаружение аномалий в событиях
10. NotificationService - сервис уведомлений
text
- send_ticket_created() - уведомление о создании тикета
- send_ticket_assigned() - уведомление о назначении
- send_ticket_updated() - уведомление об обновлении
- send_ticket_resolved() - уведомление о решении
- send_ticket_closed() - уведомление о закрытии
- send_new_message() - уведомление о новом сообщении
- send_sla_breach() - уведомление о нарушении SLA
- send_escalation() - уведомление об эскалации
- send_mention_notification() - уведомление об упоминании
- send_agent_activity() - уведомление об активности агента
- send_bulk_notifications() - массовая рассылка
- get_notification_preferences() - получение настроек уведомлений
- update_notification_preferences() - обновление настроек
- send_email() - отправка email
- send_push() - отправка push-уведомления
- send_webhook() - отправка webhook
- schedule_notification() - планирование уведомления
- get_notification_history() - история уведомлений
11. ReportService - сервис отчетности
text
- generate_daily_report() - формирование дневного отчета
- generate_weekly_report() - формирование недельного отчета
- generate_monthly_report() - формирование месячного отчета
- generate_agent_performance_report() - отчет по агентам
- generate_department_report() - отчет по отделам
- generate_sla_report() - отчет по SLA
- generate_customer_satisfaction_report() - отчет по удовлетворенности
- generate_ticket_volume_report() - отчет по объему тикетов
- export_report_pdf() - экспорт отчета в PDF
- export_report_excel() - экспорт отчета в Excel
- export_report_csv() - экспорт отчета в CSV
- schedule_report() - планирование отчета
- get_report_templates() - получение шаблонов отчетов
- create_custom_report() - создание пользовательского отчета
- get_report_by_id() - получение сохраненного отчета
- delete_report() - удаление отчета
- share_report() - публикация отчета
12. SearchService - сервис поиска
text
- search_tickets() - полнотекстовый поиск по тикетам
- search_messages() - поиск по сообщениям
- search_customers() - поиск по клиентам
- search_knowledge_base() - поиск по базе знаний
- advanced_search() - расширенный поиск с фильтрами
- index_ticket() - индексация тикета для поиска
- index_message() - индексация сообщения
- reindex_all() - переиндексация всех данных
- get_search_suggestions() - получение поисковых подсказок
- save_search() - сохранение поискового запроса
- get_saved_searches() - получение сохраненных запросов
- delete_saved_search() - удаление сохраненного запроса
- get_search_statistics() - статистика поиска
- update_search_index() - обновление индекса
13. ImportExportService - сервис импорта/экспорта
text
- import_tickets_csv() - импорт тикетов из CSV
- import_tickets_excel() - импорт из Excel
- import_tickets_json() - импорт из JSON
- export_tickets_csv() - экспорт в CSV
- export_tickets_excel() - экспорт в Excel
- export_tickets_pdf() - экспорт в PDF
- import_categories() - импорт категорий
- import_departments() - импорт отделов
- import_agents() - импорт агентов
- export_full_backup() - полный бэкап данных
- import_full_backup() - восстановление из бэкапа
- validate_import_data() - валидация данных перед импортом
- get_import_status() - статус импорта
- cancel_import() - отмена импорта
- get_export_history() - история экспортов
- schedule_export() - планирование экспорта
14. CacheService - сервис кэширования
text
- cache_ticket() - кэширование тикета
- get_cached_ticket() - получение из кэша
- invalidate_ticket_cache() - инвалидация кэша тикета
- cache_agent_session() - кэширование сессии агента
- cache_department_tree() - кэширование дерева отделов
- cache_category_tree() - кэширование дерева категорий
- cache_languages() - кэширование языков
- cache_statuses() - кэширование статусов
- get_cached_statistics() - получение кэшированной статистики
- invalidate_statistics() - инвалидация статистики
- clear_user_cache() - очистка кэша пользователя
- get_cache_stats() - статистика кэша
15. WebhookService - сервис вебхуков
text
- register_webhook() - регистрация вебхука
- update_webhook() - обновление вебхука
- delete_webhook() - удаление вебхука
- trigger_webhook() - вызов вебхука
- get_webhook_history() - история вызовов
- retry_failed_webhook() - повторная отправка
- get_webhook_statistics() - статистика вебхуков
- validate_webhook_signature() - проверка подписи
- get_webhook_events() - доступные типы событий
- pause_webhook() - приостановка вебхука
- resume_webhook() - возобновление вебхука





Описание бд
-- faq_db_v1.agents определение

CREATE TABLE `agents` (
  `id` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `full_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'ФИО сотрудника',
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Email для входа',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Хеш пароля',
  `role` enum('admin','operator','readonly') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'operator' COMMENT 'Роль пользователя',
  `department_id` smallint unsigned DEFAULT NULL COMMENT 'Департамент сотрудника',
  `is_active` tinyint unsigned NOT NULL DEFAULT '1' COMMENT 'Активен ли сотрудник',
  `phone` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Телефон',
  `avatar_path` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Путь к аватару',
  `last_login_at` timestamp NULL DEFAULT NULL COMMENT 'Последний вход',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_email` (`email`),
  KEY `idx_department` (`department_id`),
  KEY `idx_active` (`is_active`),
  KEY `idx_role` (`role`),
  CONSTRAINT `fk_agents_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Сотрудники поддержки';

-- faq_db_v1.attachments определение

CREATE TABLE `attachments` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `message_id` int unsigned NOT NULL,
  `original_filename` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `stored_filename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_size` int unsigned NOT NULL,
  `mime_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `file_hash` char(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uploaded_by_agent_id` mediumint unsigned DEFAULT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `download_count` int unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_message` (`message_id`),
  KEY `idx_uploaded_by` (`uploaded_by_agent_id`),
  KEY `idx_hash` (`file_hash`),
  KEY `idx_stored_filename` (`stored_filename`),
  CONSTRAINT `fk_attachments_agent` FOREIGN KEY (`uploaded_by_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- faq_db_v1.departments определение

CREATE TABLE `departments` (
  `id` smallint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Название департамента',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT 'Описание',
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Email для уведомлений',
  `is_active` tinyint unsigned NOT NULL DEFAULT '1' COMMENT 'Активен ли департамент',
  `sort_order` smallint unsigned NOT NULL DEFAULT '0' COMMENT 'Порядок сортировки',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_active` (`is_active`),
  KEY `idx_sort` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Департаменты поддержки';

-- faq_db_v1.languages определение

CREATE TABLE `languages` (
  `id` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `native_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `locale` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_active` tinyint unsigned NOT NULL DEFAULT '1',
  `is_default` tinyint unsigned NOT NULL DEFAULT '0',
  `sort_order` tinyint unsigned NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_is_default` (`is_default`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- faq_db_v1.messages определение

CREATE TABLE `messages` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `ticket_id` mediumint unsigned NOT NULL,
  `agent_id` mediumint unsigned DEFAULT NULL,
  `customer_name` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subject` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `body` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_internal` tinyint unsigned NOT NULL DEFAULT '0',
  `is_automatic` tinyint unsigned NOT NULL DEFAULT '0',
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket` (`ticket_id`),
  KEY `idx_agent` (`agent_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_internal` (`is_internal`),
  KEY `idx_ticket_created` (`ticket_id`,`created_at`),
  CONSTRAINT `fk_messages_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- faq_db_v1.question_categories определение

CREATE TABLE `question_categories` (
  `id` smallint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Название категории',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT 'Описание категории',
  `department_id` smallint unsigned DEFAULT NULL COMMENT 'Привязка к департаменту',
  `parent_id` smallint unsigned DEFAULT NULL COMMENT 'Родительская категория (для иерархии)',
  `icon` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Иконка категории',
  `color` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT '#999999' COMMENT 'Цвет для UI',
  `is_active` tinyint unsigned NOT NULL DEFAULT '1',
  `sort_order` smallint unsigned NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_department` (`department_id`),
  KEY `idx_parent` (`parent_id`),
  KEY `idx_active` (`is_active`),
  KEY `idx_sort` (`sort_order`),
  CONSTRAINT `fk_qcat_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_qcat_parent` FOREIGN KEY (`parent_id`) REFERENCES `question_categories` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Категории вопросов клиентов';

-- faq_db_v1.ticket_events определение

CREATE TABLE `ticket_events` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `ticket_id` mediumint unsigned NOT NULL,
  `agent_id` mediumint unsigned DEFAULT NULL,
  `action_type` enum('created','replied','status_changed','priority_changed','assigned','unassigned','category_changed','merged','closed','reopened','locked','unlocked','note_added','attachment_added','customer_replied') COLLATE utf8mb4_unicode_ci NOT NULL,
  `field_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `old_value` text COLLATE utf8mb4_unicode_ci,
  `new_value` text COLLATE utf8mb4_unicode_ci,
  `comment` text COLLATE utf8mb4_unicode_ci,
  `occurred_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket` (`ticket_id`),
  KEY `idx_agent` (`agent_id`),
  KEY `idx_action_type` (`action_type`),
  KEY `idx_occurred_at` (`occurred_at`),
  KEY `idx_ticket_occurred` (`ticket_id`,`occurred_at`),
  CONSTRAINT `fk_events_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- faq_db_v1.ticket_statuses определение

CREATE TABLE `ticket_statuses` (
  `id` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `color` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT '#999999',
  `is_closed` tinyint unsigned NOT NULL DEFAULT '0',
  `is_default` tinyint unsigned NOT NULL DEFAULT '0',
  `sort_order` tinyint unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_is_default` (`is_default`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- faq_db_v1.tickets определение

CREATE TABLE `tickets` (
  `id` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `track_id` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Уникальный публичный идентификатор',
  `customer_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Имя клиента',
  `customer_email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Email клиента',
  `customer_ip` varchar(45) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'IP адрес клиента',
  `department_id` smallint unsigned NOT NULL COMMENT 'Департамент',
  `language_id` tinyint unsigned DEFAULT NULL COMMENT 'Язык обращения',
  `category_id` smallint unsigned DEFAULT NULL COMMENT 'Категория вопроса',
  `status_id` tinyint unsigned NOT NULL DEFAULT '1' COMMENT 'Статус тикета',
  `priority` enum('low','normal','high','urgent') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'normal' COMMENT 'Приоритет',
  `subject` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Тема обращения',
  `preview_message` text COLLATE utf8mb4_unicode_ci COMMENT 'Превью первого сообщения',
  `owner_id` mediumint unsigned DEFAULT NULL COMMENT 'Ответственный агент',
  `opened_by_id` mediumint unsigned DEFAULT NULL COMMENT 'Кто создал (агент или NULL)',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `first_responded_at` timestamp NULL DEFAULT NULL COMMENT 'Первый ответ агента',
  `closed_at` timestamp NULL DEFAULT NULL COMMENT 'Время закрытия',
  `closed_by_id` mediumint unsigned DEFAULT NULL COMMENT 'Кто закрыл',
  `is_archived` tinyint unsigned NOT NULL DEFAULT '0' COMMENT 'В архиве',
  `is_locked` tinyint unsigned NOT NULL DEFAULT '0' COMMENT 'Заблокирован для ответов',
  `merged_into_id` mediumint unsigned DEFAULT NULL COMMENT 'Ссылка на главный тикет',
  `messages_count` smallint unsigned NOT NULL DEFAULT '0' COMMENT 'Количество сообщений',
  `attachments_count` smallint unsigned NOT NULL DEFAULT '0' COMMENT 'Количество вложений',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_track_id` (`track_id`),
  KEY `idx_department` (`department_id`),
  KEY `idx_status` (`status_id`),
  KEY `idx_priority` (`priority`),
  KEY `idx_owner` (`owner_id`),
  KEY `idx_customer_email` (`customer_email`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_merged` (`merged_into_id`),
  KEY `idx_archived` (`is_archived`),
  KEY `idx_status_created` (`status_id`,`created_at`),
  KEY `idx_owner_status` (`owner_id`,`status_id`),
  KEY `fk_tickets_opened_by` (`opened_by_id`),
  KEY `fk_tickets_closed_by` (`closed_by_id`),
  KEY `idx_language` (`language_id`),
  KEY `idx_category` (`category_id`),
  CONSTRAINT `fk_tickets_category` FOREIGN KEY (`category_id`) REFERENCES `question_categories` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_tickets_closed_by` FOREIGN KEY (`closed_by_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_tickets_department` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_tickets_language` FOREIGN KEY (`language_id`) REFERENCES `languages` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_tickets_merged` FOREIGN KEY (`merged_into_id`) REFERENCES `tickets` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_tickets_opened_by` FOREIGN KEY (`opened_by_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_tickets_owner` FOREIGN KEY (`owner_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_tickets_status` FOREIGN KEY (`status_id`) REFERENCES `ticket_statuses` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Тикеты обращений';