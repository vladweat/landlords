"""Unit-тесты EmailService."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import EmailService


@pytest.fixture
def email_service():
    return EmailService()


class TestEmailServiceFileFallback:
    def test_write_file_when_smtp_unset(self, email_service, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)

        email_service.send("user@example.com", "Тема", "Текст письма")

        out = tmp_path / "storage" / "emails"
        files = list(out.glob("*.txt"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert "user@example.com" in content
        assert "Тема" in content
        assert "Текст письма" in content

    def test_password_reset_template(self, email_service, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)

        email_service.send_password_reset("a@b.c", "http://localhost/reset?token=xyz")
        files = list((tmp_path / "storage" / "emails").glob("*.txt"))
        assert "Сброс пароля" in files[0].read_text(encoding="utf-8")
        assert "token=xyz" in files[0].read_text(encoding="utf-8")


class TestEmailServiceSmtp:
    def test_smtp_send(self, email_service, monkeypatch):
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", "smtp.test")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_PORT", 587)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_USER", "u")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_PASSWORD", "p")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_FROM", "from@test")

        smtp_instance = MagicMock()
        smtp_cm = MagicMock()
        smtp_cm.__enter__.return_value = smtp_instance
        smtp_cm.__exit__.return_value = False

        with patch("app.services.email_service.smtplib.SMTP", return_value=smtp_cm) as smtp_cls:
            email_service.send("to@test", "Subj", "Body")

        smtp_cls.assert_called_once_with("smtp.test", 587)
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("u", "p")
        smtp_instance.send_message.assert_called_once()
