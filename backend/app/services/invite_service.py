"""Сервис приглашений в аккаунт."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, GoneError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.domain.entities import AccountInviteEntity, MembershipEntity, UserEntity
from app.domain.interfaces import (
    IAccountInviteRepository,
    IAccountRepository,
    IMembershipRepository,
    IUserRepository,
)
from app.domain.permissions import ASSIGNABLE_ROLES, Role
from app.services.dto.invite_dto import (
    InviteAcceptDTO,
    InviteCreateDTO,
    InviteDTO,
    InvitePreviewDTO,
)
from app.services.dto.user_dto import UserDTO
from app.services.auth_session_service import AuthSessionService
from app.services.email_service import EmailService
from app.db.tenant_context import set_tenant_context
from loguru import logger

if TYPE_CHECKING:
    from app.services.plan_limit_service import PlanLimitService

ROLE_LABELS_RU = {
    Role.MANAGER.value: "менеджер",
    Role.ACCOUNTANT.value: "бухгалтер",
}

INVITE_TTL_DAYS = 7


class InviteService:
    """Создание, отзыв и принятие invite по ссылке."""

    def __init__(
        self,
        invite_repo: IAccountInviteRepository,
        account_repo: IAccountRepository,
        user_repo: IUserRepository,
        membership_repo: IMembershipRepository,
        auth_session_service: AuthSessionService,
        email_service: EmailService | None = None,
        plan_limit_service: PlanLimitService | None = None,
        session: Session | None = None,
    ) -> None:
        self.invite_repo = invite_repo
        self.account_repo = account_repo
        self.user_repo = user_repo
        self.membership_repo = membership_repo
        self.auth_session_service = auth_session_service
        self.email_service = email_service or EmailService()
        self.plan_limit_service = plan_limit_service
        self.session = session

    def create_invite(
        self, account_id: UUID, invited_by_user_id: UUID, dto: InviteCreateDTO
    ) -> InviteDTO:
        """Создать приглашение и отправить письмо."""
        try:
            role = Role(dto.role)
        except ValueError as exc:
            raise ValidationError(f"Недопустимая роль: {dto.role}") from exc
        if role not in ASSIGNABLE_ROLES:
            raise ValidationError("Можно назначить только роли manager или accountant")

        email = str(dto.email).lower().strip()
        if self.user_repo.get_by_email(email):
            raise ConflictError(f"Пользователь с email '{email}' уже существует")

        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")

        existing = self.invite_repo.get_pending_by_email(account_id, email)
        if existing:
            self.invite_repo.delete(existing.id, account_id)

        if self.plan_limit_service:
            self.plan_limit_service.assert_can_add_user(account_id, for_invite=True)

        now = datetime.now(timezone.utc)
        entity = AccountInviteEntity(
            id=uuid4(),
            account_id=account_id,
            email=email,
            full_name=dto.full_name.strip(),
            role=role.value,
            token=secrets.token_urlsafe(32),
            expires_at=now + timedelta(days=INVITE_TTL_DAYS),
            invited_by_user_id=invited_by_user_id,
        )
        created = self.invite_repo.create(entity)
        invite_dto = self._to_dto(created)

        inviter = self.user_repo.get_by_id(invited_by_user_id)
        inviter_name = inviter.full_name if inviter else "Владелец"
        email_sent = False
        try:
            self.email_service.send_invite(
                to=email,
                invite_link=invite_dto.invite_url,
                account_name=account.name,
                role_label=ROLE_LABELS_RU.get(role.value, role.value),
                inviter_name=inviter_name,
            )
            email_sent = True
        except Exception:
            logger.exception("Failed to send invite email to={}", email)

        return invite_dto.model_copy(update={"email_sent": email_sent})

    def list_pending(self, account_id: UUID) -> list[InviteDTO]:
        """Список активных приглашений."""
        return [self._to_dto(i) for i in self.invite_repo.list_pending(account_id)]

    def revoke(self, account_id: UUID, invite_id: UUID) -> None:
        """Отозвать приглашение."""
        invite = self.invite_repo.get_by_id(invite_id, account_id)
        if not invite:
            raise NotFoundError("Приглашение не найдено")
        if invite.accepted_at is not None:
            raise GoneError("Приглашение уже принято")
        self.invite_repo.delete(invite_id, account_id)

    def get_preview(self, token: str) -> InvitePreviewDTO:
        """Публичный preview приглашения."""
        self._set_context_for_invite(token)
        invite = self._get_valid_invite(token)
        account = self.account_repo.get_by_id(invite.account_id)
        if not account:
            raise NotFoundError("Аккаунт не найден")
        return InvitePreviewDTO(
            email=invite.email,
            full_name=invite.full_name,
            role=invite.role,
            account_name=account.name,
            expires_at=invite.expires_at,
        )

    def accept(self, token: str, dto: InviteAcceptDTO) -> tuple[UserDTO, str]:
        """Принять приглашение: создать user + membership, вернуть JWT."""
        self._set_context_for_invite(token)
        invite = self._get_valid_invite(token)

        if self.user_repo.get_by_email(invite.email):
            raise ConflictError(f"User with email '{invite.email}' already exists")

        if len(dto.password) < 6:
            raise ValidationError("Пароль должен быть не менее 6 символов")

        full_name = (dto.full_name or invite.full_name).strip()
        if not full_name:
            raise ValidationError("Имя обязательно")

        if self.plan_limit_service:
            self.plan_limit_service.assert_can_add_user(
                invite.account_id, for_invite=False
            )

        user = self.user_repo.create(
            UserEntity(
                id=uuid4(),
                email=invite.email,
                password_hash=hash_password(dto.password),
                full_name=full_name,
            )
        )
        self.membership_repo.create(
            MembershipEntity(
                id=uuid4(),
                account_id=invite.account_id,
                user_id=user.id,
                role=invite.role,
            )
        )
        invite.accepted_at = datetime.now(timezone.utc)
        self.invite_repo.update(invite)

        jwt = self.auth_session_service.issue_access_token(user.id, invite.account_id)
        return UserDTO.model_validate(user), jwt

    def _set_context_for_invite(self, token: str) -> None:
        if self.session is None:
            return
        account_id = self.session.execute(
            text("SELECT app_account_id_for_invite_token(:token)"),
            {"token": token},
        ).scalar_one_or_none()
        if account_id is None:
            raise NotFoundError("Приглашение не найдено")
        set_tenant_context(self.session, UUID(str(account_id)))

    def _get_valid_invite(self, token: str) -> AccountInviteEntity:
        invite = self.invite_repo.get_by_token(token)
        if not invite:
            raise NotFoundError("Приглашение не найдено")
        if invite.accepted_at is not None:
            raise GoneError("Приглашение уже принято")
        expires = invite.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            raise GoneError("Срок действия приглашения истёк")
        return invite

    def _to_dto(self, entity: AccountInviteEntity) -> InviteDTO:
        frontend = settings.FRONTEND_URL.rstrip("/")
        return InviteDTO(
            id=entity.id,
            account_id=entity.account_id,
            email=entity.email,
            full_name=entity.full_name,
            role=entity.role,
            token=entity.token,
            invite_url=f"{frontend}/invite#token={entity.token}",
            expires_at=entity.expires_at,
            invited_by_user_id=entity.invited_by_user_id,
            created_at=entity.created_at,
        )
