"""Сервис аккаунта и участников."""

from uuid import UUID, uuid4

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.domain.entities import MembershipEntity, UserEntity
from app.domain.interfaces import IAccountRepository, IMembershipRepository, IUserRepository
from app.domain.permissions import ASSIGNABLE_ROLES, Role
from app.services.dto.account_dto import AccountDTO
from app.services.dto.membership_dto import (
    AccountUpdateDTO,
    MemberCreateDTO,
    MemberDTO,
    MemberUpdateDTO,
)


class AccountService:
    """Управление аккаунтом и командой."""

    def __init__(
        self,
        account_repo: IAccountRepository,
        membership_repo: IMembershipRepository,
        user_repo: IUserRepository,
    ) -> None:
        self.account_repo = account_repo
        self.membership_repo = membership_repo
        self.user_repo = user_repo

    def get_account(self, account_id: UUID) -> AccountDTO:
        """Получить аккаунт."""
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")
        return AccountDTO.model_validate(account)

    def update_account(self, account_id: UUID, dto: AccountUpdateDTO) -> AccountDTO:
        """Обновить настройки аккаунта (только owner)."""
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")
        if dto.name is not None:
            account.name = dto.name
        if dto.base_currency is not None:
            if len(dto.base_currency) != 3:
                raise ValidationError("Валюта должна быть кодом из 3 символов")
            account.base_currency = dto.base_currency.upper()
        if dto.timezone is not None:
            account.timezone = dto.timezone
        updated = self.account_repo.update(account)
        return AccountDTO.model_validate(updated)

    def list_members(self, account_id: UUID) -> list[MemberDTO]:
        """Список участников аккаунта."""
        memberships = self.membership_repo.list_by_account(account_id)
        result: list[MemberDTO] = []
        for m in memberships:
            user = self.user_repo.get_by_id(m.user_id)
            if not user:
                continue
            result.append(
                MemberDTO(
                    user_id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    phone=user.phone,
                    role=m.role,
                    is_active=m.is_active and user.is_active,
                    membership_id=m.id,
                    created_at=m.created_at,
                )
            )
        return result

    def create_member(self, account_id: UUID, dto: MemberCreateDTO) -> MemberDTO:
        """Создать пользователя и membership (manager/accountant)."""
        try:
            role = Role(dto.role)
        except ValueError as exc:
            raise ValidationError(f"Недопустимая роль: {dto.role}") from exc
        if role not in ASSIGNABLE_ROLES:
            raise ValidationError("Можно назначить только роли manager или accountant")

        existing = self.user_repo.get_by_email(dto.email)
        if existing:
            raise ConflictError(f"User with email '{dto.email}' already exists")

        if len(dto.password) < 6:
            raise ValidationError("Пароль должен быть не менее 6 символов")

        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")

        user = self.user_repo.create(
            UserEntity(
                id=uuid4(),
                email=dto.email,
                password_hash=hash_password(dto.password),
                full_name=dto.full_name,
            )
        )
        membership = self.membership_repo.create(
            MembershipEntity(
                id=uuid4(),
                account_id=account_id,
                user_id=user.id,
                role=role.value,
            )
        )
        return MemberDTO(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=membership.role,
            is_active=True,
            membership_id=membership.id,
            created_at=membership.created_at,
        )

    def update_member_role(
        self, account_id: UUID, target_user_id: UUID, dto: MemberUpdateDTO
    ) -> MemberDTO:
        """Сменить роль участника."""
        try:
            role = Role(dto.role)
        except ValueError as exc:
            raise ValidationError(f"Недопустимая роль: {dto.role}") from exc
        if role not in ASSIGNABLE_ROLES:
            raise ValidationError("Можно назначить только роли manager или accountant")

        membership = self.membership_repo.get_by_user_and_account(target_user_id, account_id)
        if not membership:
            raise NotFoundError("Участник не найден")
        if membership.role == Role.OWNER.value:
            raise ForbiddenError("Нельзя изменить роль владельца")

        membership.role = role.value
        updated = self.membership_repo.update(membership)
        user = self.user_repo.get_by_id(target_user_id)
        if not user:
            raise NotFoundError("Пользователь не найден")
        return MemberDTO(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=updated.role,
            is_active=updated.is_active and user.is_active,
            membership_id=updated.id,
            created_at=updated.created_at,
        )

    def remove_member(self, account_id: UUID, target_user_id: UUID) -> None:
        """Удалить участника из аккаунта (membership + user)."""
        membership = self.membership_repo.get_by_user_and_account(target_user_id, account_id)
        if not membership:
            raise NotFoundError("Участник не найден")
        if membership.role == Role.OWNER.value:
            raise ForbiddenError("Нельзя удалить владельца аккаунта")

        self.membership_repo.delete(membership.id)
        self.user_repo.delete(target_user_id)
