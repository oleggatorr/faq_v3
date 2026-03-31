"""
Тесты для системы банов (email и IP).
"""
import pytest
from sqlalchemy.orm import Session

from app.models.ban import BannedEmail, BannedIP
from app.models.agent import Agent
from app.services.ban_service import BanService
from app.services.utils import ip_to_int, int_to_ip, ip_in_range, ip_to_display


class TestIPUtils:
    """Тесты утилит для работы с IP."""

    def test_ip_to_int(self):
        """Проверка конвертации IP в integer."""
        assert ip_to_int("192.168.1.1") == 3232235777
        assert ip_to_int("0.0.0.0") == 0
        assert ip_to_int("255.255.255.255") == 4294967295
        assert ip_to_int("127.0.0.1") == 2130706433

    def test_int_to_ip(self):
        """Проверка конвертации integer в IP."""
        assert int_to_ip(3232235777) == "192.168.1.1"
        assert int_to_ip(0) == "0.0.0.0"
        assert int_to_ip(4294967295) == "255.255.255.255"
        assert int_to_ip(2130706433) == "127.0.0.1"

    def test_ip_in_range(self):
        """Проверка попадания IP в диапазон."""
        # IP в диапазоне
        assert ip_in_range("192.168.1.50", ip_to_int("192.168.1.1"), ip_to_int("192.168.1.100")) is True
        # IP вне диапазона
        assert ip_in_range("192.168.2.1", ip_to_int("192.168.1.1"), ip_to_int("192.168.1.100")) is False
        # Граничные значения
        assert ip_in_range("192.168.1.1", ip_to_int("192.168.1.1"), ip_to_int("192.168.1.100")) is True
        assert ip_in_range("192.168.1.100", ip_to_int("192.168.1.1"), ip_to_int("192.168.1.100")) is True

    def test_ip_to_display(self):
        """Проверка форматирования IP для отображения."""
        assert ip_to_display("192.168.1.1") == "192.168.1.1"
        assert ip_to_display("192.168.1.1", mask=3) == "192.168.1.*"
        assert ip_to_display("192.168.1.1", mask=2) == "192.168.*.*"
        assert ip_to_display("192.168.1.1", mask=1) == "192.*.*.*"


class TestBanService:
    """Тесты сервиса банов."""

    def test_add_email_ban(self, db_session: Session, test_agent: Agent):
        """Добавление email в бан-лист."""
        banned = BanService.add_email_ban(
            db=db_session,
            email="spammer@example.com",
            banned_by=test_agent.id,
            reason="Spam",
        )
        
        assert banned.email == "spammer@example.com"
        assert banned.banned_by == test_agent.id
        assert banned.reason == "Spam"
        assert banned.id is not None

    def test_is_email_banned(self, db_session: Session, test_agent: Agent):
        """Проверка наличия email в бан-листе."""
        # Добавляем бан
        BanService.add_email_ban(
            db=db_session,
            email="banned@example.com",
            banned_by=test_agent.id,
        )
        
        # Проверяем
        assert BanService.is_email_banned(db_session, "banned@example.com") is True
        assert BanService.is_email_banned(db_session, "notbanned@example.com") is False

    def test_is_email_banned_case_insensitive(self, db_session: Session, test_agent: Agent):
        """Проверка что email бан регистронезависимый."""
        BanService.add_email_ban(
            db=db_session,
            email="Test@Example.com",
            banned_by=test_agent.id,
        )
        
        assert BanService.is_email_banned(db_session, "test@example.com") is True
        assert BanService.is_email_banned(db_session, "TEST@EXAMPLE.COM") is True

    def test_add_email_ban_duplicate(self, db_session: Session, test_agent: Agent):
        """Попытка добавить дубликат email в бан-лист."""
        BanService.add_email_ban(
            db=db_session,
            email="duplicate@example.com",
            banned_by=test_agent.id,
        )
        
        with pytest.raises(ValueError, match="уже забанен"):
            BanService.add_email_ban(
                db=db_session,
                email="duplicate@example.com",
                banned_by=test_agent.id,
            )

    def test_remove_email_ban(self, db_session: Session, test_agent: Agent):
        """Удаление email из бан-листа."""
        banned = BanService.add_email_ban(
            db=db_session,
            email="toremove@example.com",
            banned_by=test_agent.id,
        )
        
        # Проверяем что забанен
        assert BanService.is_email_banned(db_session, "toremove@example.com") is True
        
        # Удаляем бан
        result = BanService.remove_email_ban(db_session, banned.id)
        assert result is True
        
        # Проверяем что разбанен
        assert BanService.is_email_banned(db_session, "toremove@example.com") is False

    def test_add_ip_ban_single(self, db_session: Session, test_agent: Agent):
        """Добавление одиночного IP в бан-лист."""
        banned = BanService.add_ip_ban(
            db=db_session,
            ip_from="192.168.1.100",
            banned_by=test_agent.id,
        )
        
        assert banned.ip_from == ip_to_int("192.168.1.100")
        assert banned.ip_to == ip_to_int("192.168.1.100")
        assert banned.ip_display == "192.168.1.100"

    def test_add_ip_ban_range(self, db_session: Session, test_agent: Agent):
        """Добавление диапазона IP в бан-лист."""
        banned = BanService.add_ip_ban(
            db=db_session,
            ip_from="192.168.1.1",
            ip_to="192.168.1.100",
            banned_by=test_agent.id,
        )
        
        assert banned.ip_from == ip_to_int("192.168.1.1")
        assert banned.ip_to == ip_to_int("192.168.1.100")
        assert banned.ip_display == "192.168.1.1 - 192.168.1.100"

    def test_is_ip_banned(self, db_session: Session, test_agent: Agent):
        """Проверка наличия IP в бан-листе."""
        # Добавляем бан диапазона
        BanService.add_ip_ban(
            db=db_session,
            ip_from="192.168.1.1",
            ip_to="192.168.1.100",
            banned_by=test_agent.id,
        )
        
        # Проверяем IP в диапазоне
        assert BanService.is_ip_banned(db_session, "192.168.1.50") is True
        assert BanService.is_ip_banned(db_session, "192.168.1.1") is True
        assert BanService.is_ip_banned(db_session, "192.168.1.100") is True
        
        # Проверяем IP вне диапазона
        assert BanService.is_ip_banned(db_session, "192.168.2.1") is False
        assert BanService.is_ip_banned(db_session, "192.168.0.1") is False

    def test_remove_ip_ban(self, db_session: Session, test_agent: Agent):
        """Удаление IP из бан-листа."""
        banned = BanService.add_ip_ban(
            db=db_session,
            ip_from="10.0.0.1",
            banned_by=test_agent.id,
        )
        
        # Проверяем что забанен
        assert BanService.is_ip_banned(db_session, "10.0.0.1") is True
        
        # Удаляем бан
        result = BanService.remove_ip_ban(db_session, banned.id)
        assert result is True
        
        # Проверяем что разбанен
        assert BanService.is_ip_banned(db_session, "10.0.0.1") is False

    def test_get_banned_emails(self, db_session: Session, test_agent: Agent):
        """Получение списка забаненных email."""
        BanService.add_email_ban(db=db_session, email="spam1@example.com", banned_by=test_agent.id)
        BanService.add_email_ban(db=db_session, email="spam2@example.com", banned_by=test_agent.id)
        
        banned_list = BanService.get_banned_emails(db_session)
        assert len(banned_list) >= 2
        emails = [b.email for b in banned_list]
        assert "spam1@example.com" in emails
        assert "spam2@example.com" in emails

    def test_get_banned_ips(self, db_session: Session, test_agent: Agent):
        """Получение списка забаненных IP."""
        BanService.add_ip_ban(db=db_session, ip_from="10.0.0.1", banned_by=test_agent.id)
        BanService.add_ip_ban(db=db_session, ip_from="10.0.0.2", banned_by=test_agent.id)
        
        banned_list = BanService.get_banned_ips(db_session)
        assert len(banned_list) >= 2
