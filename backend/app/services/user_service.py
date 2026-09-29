"""Сервис пользователей."""

from uuid import UUID, uuid4

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_reset_token,
    hash_password,
    verify_password,
)
from app.domain.entities import AccountEntity, MembershipEntity, UserEntity
from app.domain.interfaces import IAccountRepository, IMembershipRepository, IUserRepository
from app.domain.permissions import Role
from app.services.dto.account_dto import AccountDTO
from app.services.dto.user_dto import UserCreateDTO, UserDTO
from app.services.email_service import EmailService
from loguru import logger


class UserService:
    """Сервис управления пользователями и аутентификацией."""

    def __init__(
        self,
        user_repo: IUserRepository,
        account_repo: IAccountRepository,
        membership_repo: IMembershipRepository,
        email_service: EmailService | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.account_repo = account_repo
        self.membership_repo = membership_repo
        self.email_service = email_service or EmailService()

    def register(self, dto: UserCreateDTO) -> tuple[UserDTO, AccountDTO, str]:
        """Зарегистрировать пользователя и создать аккаунт."""
        existing = self.user_repo.get_by_email(dto.email)
        if existing:
            raise ConflictError(f"User with email '{dto.email}' already exists")

        created_user = self.user_repo.create(
            UserEntity(
                id=uuid4(),
                email=dto.email,
                password_hash=hash_password(dto.password),
                full_name=dto.full_name,
            )
        )

        created_account = self.account_repo.create(
            AccountEntity(
                id=uuid4(),
                name=f"{dto.full_name}'s Account",
                owner_id=created_user.id,
            )
        )

        self.membership_repo.create(
            MembershipEntity(
                id=uuid4(),
                account_id=created_account.id,
                user_id=created_user.id,
                role=Role.OWNER.value,
            )
        )

        token = create_access_token(
            user_id=str(created_user.id),
            account_id=str(created_account.id),
        )

        try:
            self.email_service.send_welcome(created_user.email, created_user.full_name)
        except Exception:
            logger.exception("Failed to send welcome email")

        return (
            UserDTO.model_validate(created_user),
            AccountDTO.model_validate(created_account),
            token,
        )

    def login(self, email: str, password: str) -> tuple[UserDTO, AccountDTO, str]:
        """Аутентифицировать пользователя."""
        user = self.user_repo.get_by_email(email)
        if not user:
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("User is inactive")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        membership = self.membership_repo.get_by_user_id(user.id)
        if not membership or not membership.is_active:
            raise UnauthorizedError("No active account membership")

        account = self.account_repo.get_by_id(membership.account_id)
        if not account:
            raise NotFoundError("Account not found")

        token = create_access_token(
            user_id=str(user.id),
            account_id=str(account.id),
        )

        return (
            UserDTO.model_validate(user),
            AccountDTO.model_validate(account),
            token,
        )

    def get_me(self, user_id: UUID) -> tuple[UserDTO, AccountDTO, str]:
        """Получить текущего пользователя, аккаунт и роль."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found")

        membership = self.membership_repo.get_by_user_id(user_id)
        if not membership or not membership.is_active:
            raise NotFoundError("Account membership not found")

        account = self.account_repo.get_by_id(membership.account_id)
        if not account:
            raise NotFoundError("Account not found")

        return (
            UserDTO.model_validate(user),
            AccountDTO.model_validate(account),
            membership.role,
        )

    def get_user_by_email(self, email: str) -> UserDTO | None:
        """Получить пользователя по email (для публичного использования)."""
        user = self.user_repo.get_by_email(email)
        return UserDTO.model_validate(user) if user else None

    def request_password_reset(self, email: str) -> None:
        """
        Запрос на сброс пароля: создать токен и отправить письмо.
        Не логируем сам токен. Без SMTP письмо пишется в storage/emails.
        """
        user = self.user_repo.get_by_email(email)
        if not user:
            return

        token = create_reset_token(str(user.id))
        try:
            frontend = settings.FRONTEND_URL.rstrip("/")
            reset_link = f"{frontend}/reset-password?token={token}"
            self.email_service.send_password_reset(user.email, reset_link)
            logger.info("Password reset email dispatched (no token in logs).")
        except Exception:
            logger.exception("Error while preparing password reset")

    def reset_password(self, user_id: UUID, new_password: str) -> None:
        """Сбросить пароль пользователя."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Пользователь не найден")
        if len(new_password) < 6:
            raise ValidationError("Пароль должен быть не менее 6 символов")
        user.password_hash = hash_password(new_password)
        self.user_repo.update(user)

    def update_profile(
        self,
        user_id: UUID,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> UserDTO:
        """Обновить профиль пользователя."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        if full_name is not None:
            user.full_name = full_name
        if phone is not None:
            user.phone = phone or None
        self.user_repo.update(user)
        return UserDTO.model_validate(user)

    def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        """Сменить пароль."""
        user = self.user_repo.get_by_id(user_id)
        if not user or not verify_password(current_password, user.password_hash):
            raise ValidationError("Неверный текущий пароль")
        if len(new_password) < 6:
            raise ValidationError("Пароль должен быть не менее 6 символов")
        user.password_hash = hash_password(new_password)
        self.user_repo.update(user)

    def delete_account(self, user_id: UUID, confirmation: str) -> None:
        """Удалить аккаунт (только владелец)."""
        if confirmation != "DELETE":
            raise ValidationError("Для подтверждения введите DELETE")

        membership = self.membership_repo.get_by_user_id(user_id)
        if not membership or membership.role != Role.OWNER.value:
            raise ForbiddenError("Только владелец может удалить аккаунт")

        # CASCADE: user → account (owner_id) → memberships + business data
        self.user_repo.delete(user_id)
