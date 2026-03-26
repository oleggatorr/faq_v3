"""
Сервис отправки email-уведомлений.

Временная заглушка: все письма отправляются с olegfesenko365@gmail.com
и приходят на olegfesenko365@gmail.com (независимо от реального получателя).
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

# Временная заглушка: фиксированные адреса
STUB_FROM = "olegfesenko365@gmail.com"
STUB_TO = "olegfesenko356@gmail.com"


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

    actual_to = STUB_TO

    logger.info(
        "Email: to=%s -> %s | subject=%s",
        to_list,
        actual_to,
        subject[:50],
    )

    try:
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = 'olegfesenko356@gmail.com'

        if reply_to:
            msg["Reply-To"] = reply_to
        
        if int(os.getenv("IS_DEBUG")):
            print("email suspend")
            return

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_USER, [actual_to], msg.as_string())

    except Exception as e:
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
    print(f"notify_ticket_created: to_email={to_email}, track_id={track_id}, subject={subject}, customer_name={customer_name}, body_preview={body_preview}")

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
    send_email(
        to=to_email,
        subject=f"[Статус обращения {track_id}] {subject}",
        body=f"Здравствуйте, {customer_name}.\n\n"
        f"Статус вашего обращения {track_id} изменён.\n"
        f"Новый статус: {new_status}\n\n"
        f"Тема обращения: {subject}",
    )
