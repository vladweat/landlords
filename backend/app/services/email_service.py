"""Отправка email: SMTP или файл в storage/emails (dev)."""

from __future__ import annotations

import smtplib
import ssl
import time
from email.message import EmailMessage
from pathlib import Path

from app.core.config import settings
from loguru import logger


class EmailService:
    """Единая точка отправки писем приложения."""

    SMTP_TIMEOUT_SEC = 8

    def send(self, to: str, subject: str, body_text: str) -> None:
        """Отправить письмо; файловый fallback доступен только вне production."""
        if self._smtp_settings() is None:
            if settings.APP_ENV == "production":
                raise RuntimeError("Email provider is not configured in production")
            self._write_file(to, subject, body_text)
            return

        try:
            self._send_smtp(to, subject, body_text)
        except Exception:
            logger.exception("SMTP send failed to={}", to)
            if settings.APP_ENV == "production":
                raise
            logger.warning("Falling back to storage/emails (APP_ENV != production)")
            self._write_file(to, subject, body_text)

    def _smtp_settings(self) -> tuple[str, int, str | None, str | None, str, str] | None:
        """Host, port, user, password, from, TLS mode — или None."""
        from_addr = settings.SMTP_FROM or "no-reply@example.com"
        tls_mode = settings.SMTP_TLS_MODE
        if settings.SMTP_HOST and settings.SMTP_HOST.strip():
            return (
                settings.SMTP_HOST,
                settings.SMTP_PORT or self._default_port(tls_mode),
                settings.SMTP_USER,
                settings.SMTP_PASSWORD,
                from_addr,
                tls_mode,
            )
        if settings.RESEND_API_KEY and settings.RESEND_API_KEY.strip():
            return (
                "smtp.resend.com",
                settings.SMTP_PORT or self._default_port(tls_mode),
                settings.SMTP_USER or "resend",
                settings.RESEND_API_KEY,
                from_addr,
                tls_mode,
            )
        return None

    @staticmethod
    def _default_port(tls_mode: str) -> int:
        return {"ssl": 465, "starttls": 587, "none": 25}[tls_mode]

    def send_password_reset(self, to: str, reset_link: str) -> None:
        """Письмо со ссылкой сброса пароля."""
        self.send(
            to=to,
            subject="Сброс пароля",
            body_text=(
                "Чтобы сбросить пароль, перейдите по ссылке:\n"
                f"{reset_link}\n\n"
                "Если вы не запрашивали сброс, просто проигнорируйте это письмо."
            ),
        )

    def send_welcome(self, to: str, full_name: str) -> None:
        """Приветственное письмо после регистрации."""
        frontend = settings.FRONTEND_URL.rstrip("/")
        self.send(
            to=to,
            subject="Добро пожаловать в Landlords",
            body_text=(
                f"Здравствуйте, {full_name}!\n\n"
                "Аккаунт в Landlords создан. Войти можно здесь:\n"
                f"{frontend}/login\n"
            ),
        )

    def send_invite(
        self,
        to: str,
        invite_link: str,
        account_name: str,
        role_label: str,
        inviter_name: str,
    ) -> None:
        """Приглашение в аккаунт."""
        self.send(
            to=to,
            subject=f"Приглашение в {account_name}",
            body_text=(
                f"{inviter_name} приглашает вас в аккаунт «{account_name}» "
                f"как {role_label}.\n\n"
                "Чтобы принять приглашение и задать пароль, перейдите по ссылке:\n"
                f"{invite_link}\n\n"
                "Ссылка действует 7 дней."
            ),
        )

    def send_charge_overdue(
        self,
        to: str,
        property_address: str,
        remaining: str,
        currency: str,
        tenant_name: str | None,
        contract_href: str,
    ) -> None:
        """Письмо владельцу о просроченной оплате."""
        tenant_part = f" ({tenant_name})" if tenant_name else ""
        self.send(
            to=to,
            subject=f"Просроченная оплата: {property_address}",
            body_text=(
                f"Просроченная оплата по объекту {property_address}{tenant_part}.\n"
                f"Остаток: {remaining} {currency}.\n\n"
                f"Открыть договор: {contract_href}\n"
            ),
        )

    def send_contract_ending(
        self,
        to: str,
        property_address: str,
        days_until_end: int,
        tenant_name: str | None,
        contract_href: str,
    ) -> None:
        """Письмо владельцу об окончании договора."""
        tenant_part = f" ({tenant_name})" if tenant_name else ""
        self.send(
            to=to,
            subject=f"Окончание договора: {property_address}",
            body_text=(
                f"Договор по объекту {property_address}{tenant_part} "
                f"заканчивается через {days_until_end} дн.\n\n"
                f"Открыть договор: {contract_href}\n"
            ),
        )

    def _send_smtp(self, to: str, subject: str, body_text: str) -> None:
        cfg = self._smtp_settings()
        if cfg is None:
            raise RuntimeError("SMTP is not configured")
        host, port, user, password, from_addr, tls_mode = cfg
        if settings.APP_ENV == "production" and tls_mode == "none":
            raise RuntimeError("SMTP without TLS is forbidden in production")
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        msg.set_content(body_text)
        try:
            if tls_mode == "ssl":
                smtp_factory = smtplib.SMTP_SSL
                smtp_kwargs = {"context": ssl.create_default_context()}
            else:
                smtp_factory = smtplib.SMTP
                smtp_kwargs = {}

            with smtp_factory(
                host, port, timeout=self.SMTP_TIMEOUT_SEC, **smtp_kwargs
            ) as smtp:
                if tls_mode == "starttls":
                    smtp.ehlo()
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
            logger.info("Email sent to={} subject={!r}", to, subject)
        except Exception:
            logger.exception("Failed to send email to={} subject={!r}", to, subject)
            raise

    def _write_file(self, to: str, subject: str, body_text: str) -> None:
        out_dir = Path("storage/emails")
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_to = to.replace("/", "_").replace("\\", "_")
        fname = out_dir / f"{safe_to}-{int(time.time() * 1000)}.txt"
        fname.write_text(f"To: {to}\nSubject: {subject}\n\n{body_text}", encoding="utf-8")
        logger.info("Email written to {} (SMTP unset)", fname)
