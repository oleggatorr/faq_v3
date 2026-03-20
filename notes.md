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