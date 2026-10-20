"""Unit-тесты EmailService."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import EmailService


@pytest.fixture
def email_service():
    return EmailService()


class TestEmailServiceFileFallback:
    def test_write_file_when_smtp_unset(self, email_service, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("app.services.email_service.settings.APP_ENV", "development")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", None)

        email_service.send("user@example.com", "Тема", "Текст письма")

        out = tmp_path / "storage" / "emails"
        files = list(out.glob("*.txt"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert "user@example.com" in content
        assert "Тема" in content
        assert "Текст письма" in content

    def test_production_without_provider_raises_without_writing_file(
        self, email_service, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("app.services.email_service.settings.APP_ENV", "production")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", None)

        with pytest.raises(RuntimeError, match="Email provider is not configured"):
            email_service.send("user@example.com", "Тема", "Текст")

        assert not (tmp_path / "storage" / "emails").exists()

    def test_password_reset_email_missing_provider_raises(
        self, email_service, monkeypatch
    ):
        monkeypatch.setattr("app.services.email_service.settings.APP_ENV", "production")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", None)

        with pytest.raises(RuntimeError, match="Email provider is not configured"):
            email_service.send_password_reset("a@b.c", "https://example.test/reset#token")

    def test_password_reset_template(self, email_service, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", None)

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
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", None)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_TLS_MODE", "starttls")

        smtp_instance = MagicMock()
        smtp_cm = MagicMock()
        smtp_cm.__enter__.return_value = smtp_instance
        smtp_cm.__exit__.return_value = False

        with patch("app.services.email_service.smtplib.SMTP", return_value=smtp_cm) as smtp_cls:
            email_service.send("to@test", "Subj", "Body")

        smtp_cls.assert_called_once_with("smtp.test", 587, timeout=8)
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("u", "p")
        smtp_instance.send_message.assert_called_once()

    def test_resend_api_key_uses_resend_smtp(self, email_service, monkeypatch):
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", None)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_PORT", None)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_USER", None)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_FROM", "me@domain.com")
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", "re_test")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_TLS_MODE", "starttls")

        smtp_instance = MagicMock()
        smtp_cm = MagicMock()
        smtp_cm.__enter__.return_value = smtp_instance
        smtp_cm.__exit__.return_value = False

        with patch("app.services.email_service.smtplib.SMTP", return_value=smtp_cm) as smtp_cls:
            email_service.send("to@test", "Subj", "Body")

        smtp_cls.assert_called_once_with("smtp.resend.com", 587, timeout=8)
        smtp_instance.login.assert_called_once_with("resend", "re_test")

    def test_smtp_ssl_uses_implicit_tls(self, email_service, monkeypatch):
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", "smtp.test")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_PORT", None)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_TLS_MODE", "ssl")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_USER", None)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_PASSWORD", None)

        smtp_instance = MagicMock()
        smtp_cm = MagicMock()
        smtp_cm.__enter__.return_value = smtp_instance
        smtp_cm.__exit__.return_value = False

        with patch(
            "app.services.email_service.smtplib.SMTP_SSL", return_value=smtp_cm
        ) as smtp_ssl_cls:
            with patch("app.services.email_service.smtplib.SMTP") as smtp_cls:
                email_service.send("to@test", "Subj", "Body")

        assert smtp_ssl_cls.call_args.args[:2] == ("smtp.test", 465)
        smtp_cls.assert_not_called()
        smtp_instance.starttls.assert_not_called()
        smtp_instance.send_message.assert_called_once()

    def test_starttls_failure_never_sends_without_tls(self, email_service, monkeypatch):
        monkeypatch.setattr("app.services.email_service.settings.APP_ENV", "production")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", "smtp.test")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_PORT", 587)
        monkeypatch.setattr("app.services.email_service.settings.SMTP_USER", "u")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_PASSWORD", "p")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_TLS_MODE", "starttls")

        smtp_instance = MagicMock()
        smtp_instance.starttls.side_effect = smtplib.SMTPNotSupportedError("STARTTLS unavailable")
        smtp_cm = MagicMock()
        smtp_cm.__enter__.return_value = smtp_instance
        smtp_cm.__exit__.return_value = False

        with patch("app.services.email_service.smtplib.SMTP", return_value=smtp_cm):
            with pytest.raises(smtplib.SMTPNotSupportedError):
                email_service.send("to@test", "Subj", "Body")

        smtp_instance.login.assert_not_called()
        smtp_instance.send_message.assert_not_called()

    def test_production_rejects_plain_smtp_mode(self, email_service, monkeypatch):
        monkeypatch.setattr("app.services.email_service.settings.APP_ENV", "production")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", "smtp.test")
        monkeypatch.setattr("app.services.email_service.settings.SMTP_TLS_MODE", "none")

        with patch("app.services.email_service.smtplib.SMTP") as smtp_cls:
            with pytest.raises(RuntimeError, match="without TLS is forbidden"):
                email_service.send("to@test", "Subj", "Body")

        smtp_cls.assert_not_called()
