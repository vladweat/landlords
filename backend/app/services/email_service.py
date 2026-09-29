"""Отправка email: SMTP или файл в storage/emails (dev)."""

from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from app.core.config import settings
from loguru import logger


class EmailService:
    """Единая точка отправки писем приложения."""

    def send(self, to: str, subject: str, body_text: str) -> None:
        """Отправить plain-text письмо. Без SMTP пишет в storage/emails/."""
        if settings.SMTP_HOST:
            self._send_smtp(to, subject, body_text)
        else:
            self._write_file(to, subject, body_text)

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
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM or "no-reply@example.com"
        msg["To"] = to
        msg.set_content(body_text)
        try:
            smtp_port = settings.SMTP_PORT or 25
            with smtplib.SMTP(settings.SMTP_HOST, smtp_port) as smtp:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    try:
                        smtp.starttls()
                    except Exception:
                        pass
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
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
