from enum import Enum


class Permission(str, Enum):
    can_view_tickets = "can_view_tickets"  # Просмотр деталей тикета
    can_view_own_tickets = "can_view_own_tickets"  # Просмотр списка своих тикетов
    can_reply_tickets = "can_reply_tickets"
    can_del_tickets = "can_del_tickets"
    can_hard_del_tickets = "can_hard_del_tickets"  # Полное удаление тикетов
    can_edit_tickets = "can_edit_tickets"
    can_merge_tickets = "can_merge_tickets"
    can_resolve = "can_resolve"
    can_submit_any_cat = "can_submit_any_cat"
    can_del_notes = "can_del_notes"
    can_change_cat = "can_change_cat"
    can_change_own_cat = "can_change_own_cat"
    can_man_kb = "can_man_kb"
    can_man_users = "can_man_users"
    can_man_cat = "can_man_cat"
    can_man_canned = "can_man_canned"
    can_man_ticket_tpl = "can_man_ticket_tpl"
    can_man_settings = "can_man_settings"
    can_add_archive = "can_add_archive"
    can_assign_self = "can_assign_self"
    can_assign_others = "can_assign_others"
    can_view_unassigned = "can_view_unassigned"
    can_view_ass_others = "can_view_ass_others"
    can_view_ass_by = "can_view_ass_by"
    can_run_reports = "can_run_reports"
    can_run_reports_full = "can_run_reports_full"
    can_export = "can_export"
    can_view_online = "can_view_online"
    can_ban_emails = "can_ban_emails"
    can_unban_emails = "can_unban_emails"
    can_ban_ips = "can_ban_ips"
    can_unban_ips = "can_unban_ips"
    can_privacy = "can_privacy"
    can_service_msg = "can_service_msg"
    can_email_tpl = "can_email_tpl"
    # Права для работы с агентами
    agent_view = "agent_view"
    agent_create = "agent_create"
    agent_edit = "agent_edit"
    agent_delete = "agent_delete"
    # Права для просмотра логов
    audit_logs_view = "audit_logs_view"


# 📋 Список всех прав (для генерации dict)
ALL_PERMISSIONS = list(Permission)


# 📘 Человекочитаемые названия
PERMISSION_LABELS = {
    Permission.can_view_tickets: "Просмотр тикетов (детали)",
    Permission.can_view_own_tickets: "Просмотр своих тикетов (список)",
    Permission.can_reply_tickets: "Ответ на тикеты",
    Permission.can_del_tickets: "Удаление тикетов (архив)",
    Permission.can_hard_del_tickets: "Полное удаление тикетов",
    Permission.can_edit_tickets: "Редактирование тикетов",
    Permission.can_merge_tickets: "Объединение тикетов",
    Permission.can_resolve: "Закрытие (решение) тикетов",
    Permission.can_submit_any_cat: "Создание тикетов в любых категориях",
    Permission.can_del_notes: "Удаление заметок",
    Permission.can_change_cat: "Изменение категории тикета",
    Permission.can_change_own_cat: "Изменение своей категории",
    Permission.can_man_kb: "Управление базой знаний",
    Permission.can_man_users: "Управление пользователями",
    Permission.can_man_cat: "Управление категориями",
    Permission.can_man_canned: "Управление шаблонными ответами",
    Permission.can_man_ticket_tpl: "Управление шаблонами тикетов",
    Permission.can_man_settings: "Управление настройками системы",
    Permission.can_add_archive: "Добавление в архив",
    Permission.can_assign_self: "Назначение тикета себе",
    Permission.can_assign_others: "Назначение тикетов другим",
    Permission.can_view_unassigned: "Просмотр неназначенных тикетов",
    Permission.can_view_ass_others: "Просмотр тикетов других операторов",
    Permission.can_view_ass_by: "Просмотр назначенных по пользователю",
    Permission.can_run_reports: "Просмотр отчетов",
    Permission.can_run_reports_full: "Полный доступ к отчетам",
    Permission.can_export: "Экспорт данных",
    Permission.can_view_online: "Просмотр онлайн-операторов",
    Permission.can_ban_emails: "Блокировка email",
    Permission.can_unban_emails: "Разблокировка email",
    Permission.can_ban_ips: "Блокировка IP",
    Permission.can_unban_ips: "Разблокировка IP",
    Permission.can_privacy: "Управление приватностью",
    Permission.can_service_msg: "Системные сообщения",
    Permission.can_email_tpl: "Управление email-шаблонами",
    Permission.agent_view: "Просмотр агентов",
    Permission.agent_create: "Создание агентов",
    Permission.agent_edit: "Редактирование агентов",
    Permission.agent_delete: "Удаление агентов",
    Permission.audit_logs_view: "Просмотр логов аудита",
}


# 📂 Группировка (очень удобно для UI)
PERMISSION_GROUPS = {
    "Тикеты": [
        Permission.can_view_own_tickets,  # Просмотр списка своих тикетов
        Permission.can_view_tickets,  # Просмотр деталей тикета
        Permission.can_reply_tickets,
        Permission.can_edit_tickets,
        Permission.can_del_tickets,
        Permission.can_merge_tickets,
        Permission.can_resolve,
        Permission.can_submit_any_cat,
        Permission.can_change_cat,
        Permission.can_change_own_cat,
    ],
    "Назначение": [
        Permission.can_assign_self,
        Permission.can_assign_others,
        Permission.can_view_unassigned,
        Permission.can_view_ass_others,
        Permission.can_view_ass_by,
    ],
    "Заметки и архив": [
        Permission.can_del_notes,
        Permission.can_add_archive,
    ],
    "Администрирование": [
        Permission.can_man_users,
        Permission.can_man_cat,
        Permission.can_man_kb,
        Permission.can_man_canned,
        Permission.can_man_ticket_tpl,
        Permission.can_man_settings,
    ],
    "Отчёты и данные": [
        Permission.can_run_reports,
        Permission.can_run_reports_full,
        Permission.can_export,
    ],
    "Безопасность": [
        Permission.can_ban_emails,
        Permission.can_unban_emails,
        Permission.can_ban_ips,
        Permission.can_unban_ips,
        Permission.can_privacy,
    ],
    "Прочее": [
        Permission.can_view_online,
        Permission.can_service_msg,
        Permission.can_email_tpl,
    ],
    "Агенты": [
        Permission.agent_view,
        Permission.agent_create,
        Permission.agent_edit,
        Permission.agent_delete,
    ],
    "Аудит": [
        Permission.audit_logs_view,
    ],
}


# 📦 Наборы прав по умолчанию
DEFAULT_OPERATOR_PERMISSIONS = [
    Permission.can_view_tickets,
    Permission.can_reply_tickets,
    Permission.can_edit_tickets,
    Permission.can_del_tickets,  # Архивирование
    Permission.can_hard_del_tickets,  # Полное удаление
    Permission.can_resolve,
    Permission.can_assign_self,
    Permission.can_view_ass_others,
    Permission.agent_view,
    Permission.agent_edit,
    Permission.agent_delete,
]


DEFAULT_READONLY_PERMISSIONS = [
    Permission.can_view_tickets,
    Permission.can_view_ass_others,
    Permission.agent_view,
]


# 🔐 Проверка прав
def has_permission(agent, permission: Permission) -> bool:
    """
    Проверить наличие права у агента.
    Администратор всегда имеет все права.
    """
    # Админ имеет всё (проверяем и строку, и AgentRole)
    role = getattr(agent, "role", None)
    if role == "admin" or str(role) == "admin":
        return True
    
    if not agent.permissions:
        return False

    user_perms = set(agent.permissions.split(","))
    return permission.value in user_perms


# 🔧 Получить список прав пользователя
def get_agent_permissions(agent) -> set[str]:
    """Получить набор прав агента."""
    if not agent.permissions:
        return set()
    return set(agent.permissions.split(","))


# 🔧 Проверка роли
def is_admin(agent) -> bool:
    """Проверить, является ли агент администратором."""
    role = getattr(agent, "role", None)
    return role == "admin" or str(role) == "admin"