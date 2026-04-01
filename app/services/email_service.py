"""
Сервис отправки email-уведомлений.
"""
from __future__ import annotations

import logging
from typing import Sequence
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# В DEBUG режиме письма отправляются на реальный адрес получателя
# В production можно использовать заглушку
IS_DEBUG = int(os.getenv("IS_DEBUG", 0))
STUB_TO = "olegfesenko356@gmail.com" if not IS_DEBUG else None

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

logger = logging.getLogger(__name__)


def send_email(
    *,
    to: str | Sequence[str],
    subject: str,
    body: str,
    reply_to: str | None = None,
) -> None:
    if isinstance(to, str):
        to_list = [to]
    else:
        to_list = list(to)

    # В DEBUG режиме отправляем на реальный адрес, иначе на заглушку
    if IS_DEBUG:
        actual_to = to_list
    else:
        actual_to = [STUB_TO]

    print(f"\n📧 Отправка сообщения:")
    print(f"   Откуда: {EMAIL_USER}")
    print(f"   Куда (реальный): {to_list}")
    print(f"   Куда (фактический): {actual_to}")
    print(f"   Тема: {subject}")
    print(f"   Тело: {body[:300]}{'...' if len(body) > 300 else ''}")

    logger.info(
        "Email: to=%s | subject=%s",
        to_list,
        subject[:50],
    )

    try:
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to if isinstance(to, str) else ', '.join(to_list)

        if reply_to:
            msg["Reply-To"] = reply_to

        if IS_DEBUG:
            print("   ℹ️ DEBUG MODE: Письмо отправляется на реальный адрес")
        else:
            print("   ℹ️ PRODUCTION MODE: Письмо отправляется на заглушку")

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_USER, actual_to, msg.as_string())
            print("   ✅ Письмо успешно отправлено!")

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        logger.exception("Ошибка отправки email: %s", e)


def notify_ticket_created(
    *,
    to_email: str,
    track_id: str,
    subject: str,
    customer_name: str,
    body_preview: str,
) -> None:
    """Уведомление о создании тикета (на почту департамента)."""
    print(f"\n📬 notify_ticket_created вызван:")
    print(f"   to_email={to_email}")
    print(f"   track_id={track_id}")
    print(f"   subject={subject}")
    print(f"   customer_name={customer_name}")
    print(f"   body_preview={body_preview[:100]}...")

    send_email(
        to=to_email,
        subject=f"[Новое обращение {track_id}] {subject}",
        body=f"Создано новое обращение.\n\n"
        f"Трек-номер: {track_id}\n"
        f"От: {customer_name}\n"
        f"Тема: {subject}\n\n"
        f"Сообщение:\n{body_preview[:500]}{'...' if len(body_preview) > 500 else ''}",
    )


def notify_new_message(
    *,
    to_email: str,
    track_id: str,
    subject: str,
    message_preview: str,
    from_name: str,
) -> None:
    """Уведомление о новом сообщении по тикету (оператору или департаменту)."""
    print(f"\n📬 notify_new_message вызван:")
    print(f"   to_email={to_email}")
    print(f"   track_id={track_id}")
    print(f"   subject={subject}")
    print(f"   from_name={from_name}")
    print(f"   message_preview={message_preview[:100]}...")

    send_email(
        to=to_email,
        subject=f"[Новое сообщение {track_id}] {subject}",
        body=f"Новое сообщение по обращению {track_id}.\n\n"
        f"От: {from_name}\n"
        f"Тема: {subject}\n\n"
        f"Сообщение:\n{message_preview[:500]}{'...' if len(message_preview) > 500 else ''}",
    )


def notify_status_changed(
    *,
    to_email: str,
    track_id: str,
    subject: str,
    new_status: str,
    customer_name: str,
) -> None:
    """Уведомление об изменении статуса (заявителю)."""
    print(f"\n📬 notify_status_changed вызван:")
    print(f"   to_email={to_email}")
    print(f"   track_id={track_id}")
    print(f"   subject={subject}")
    print(f"   new_status={new_status}")
    print(f"   customer_name={customer_name}")

    send_email(
        to=to_email,
        subject=f"[Статус обращения {track_id}] {subject}",
        body=f"Здравствуйте, {customer_name}.\n\n"
        f"Статус вашего обращения {track_id} изменён.\n"
        f"Новый статус: {new_status}\n\n"
        f"Тема обращения: {subject}",
    )


def notify_ticket_assigned(
    *,
    to_email: str,
    track_id: str,
    subject: str,
    assigned_by: int | None = None,
) -> None:
    """Уведомление оператора о назначении тикета."""
    print(f"\n📬 notify_ticket_assigned вызван:")
    print(f"   to_email={to_email}")
    print(f"   track_id={track_id}")
    print(f"   subject={subject}")
    print(f"   assigned_by={assigned_by}")

    send_email(
        to=to_email,
        subject=f"[Назначен тикет {track_id}] {subject}",
        body=f"Вам назначено новое обращение.\n\n"
        f"Трек-номер: {track_id}\n"
        f"Тема: {subject}\n\n"
        f"Пожалуйста, обработайте обращение в ближайшее время.",
    )


def notify_ticket_created_customer(
    *,
    to_email: str,
    track_id: str,
    subject: str,
    customer_name: str,
) -> None:
    """Уведомление пользователя о создании тикета (подтверждение)."""
    print(f"\n📬 notify_ticket_created_customer вызван:")
    print(f"   to_email={to_email}")
    print(f"   track_id={track_id}")
    print(f"   subject={subject}")
    print(f"   customer_name={customer_name}")

    send_email(
        to=to_email,
        subject=f"[Заявка принята {track_id}] {subject}",
        body=f"Здравствуйте, {customer_name}!\n\n"
        f"Ваше обращение принято в работу.\n\n"
        f"Трек-номер: {track_id}\n"
        f"Тема: {subject}\n\n"
        f"Сохраните трек-номер для отслеживания статуса обращения.\n"
        f"Вы получите уведомление при изменении статуса или получении ответа.",
    )
