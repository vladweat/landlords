"""Сервис пользователей."""

from uuid import UUID, uuid4

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.repositories.account_repo import AccountRepository
from app.domain.entities import AccountEntity, UserEntity
from app.domain.interfaces import IUserRepository
from app.services.dto.account_dto import AccountCreateDTO, AccountDTO
from app.services.dto.user_dto import UserCreateDTO, UserDTO

class UserService:
    """Сервис управления пользователями и аутентификацией."""

    def __init__(
        self,
        user_repo: IUserRepository,
        account_repo: AccountRepository,
    ) -> None:
        self.user_repo = user_repo
        self.account_repo = account_repo

    def register(self, dto: UserCreateDTO) -> tuple[UserDTO, AccountDTO, str]:
        """Зарегистрировать пользователя и создать аккаунт."""
        # Проверяем уникальность email
        existing = self.user_repo.get_by_email(dto.email)
        if existing:
            raise ConflictError(f"User with email '{dto.email}' already exists")

        # Создаём пользователя
        user_entity = UserEntity(
            id=uuid4(),
            email=dto.email,
            password_hash=hash_password(dto.password),
            full_name=dto.full_name,
        )
        created_user = self.user_repo.create(user_entity)

        # Создаём аккаунт
        account_entity = AccountEntity(
            id=uuid4(),
            name=f"{dto.full_name}'s Account",
            owner_id=created_user.id,
        )
        created_account = self.account_repo.create(account_entity)

        # Генерируем токен
        token = create_access_token(
            user_id=str(created_user.id),
            account_id=str(created_account.id),
        )

        return (
            UserDTO.model_validate(created_user),
            AccountDTO.model_validate(created_account),
            token,
        )

    def login(self, email: str, password: str) -> tuple[UserDTO, AccountDTO, str]:
        """Аутентифицировать пользователя."""
        user = self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundError("Invalid email or password")

        if not verify_password(password, user.password_hash):
            raise NotFoundError("Invalid email or password")

        account_entity = self.account_repo.get_by_owner_id(user.id)
        if not account_entity:
            raise NotFoundError("Account not found")

        token = create_access_token(
            user_id=str(user.id),
            account_id=str(account_entity.id),  # ← было account.id, account — это функция
        )

        return (
            UserDTO.model_validate(user),
            AccountDTO.model_validate(account_entity),
            token,
        )

    def get_me(self, user_id: UUID) -> tuple[UserDTO, AccountDTO]:
        """Получить текущего пользователя и его аккаунт."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found")

        account = self.account_repo.get_by_owner_id(user_id)
        if not account:
            raise NotFoundError("Account not found")

        return (
            UserDTO.model_validate(user),
            AccountDTO.model_validate(account),
        )
        
    def get_user_by_email(self, email: str) -> UserDTO | None:
        """Получить пользователя по email (для публичного использования)."""
        user = self.user_repo.get_by_email(email)
        return UserDTO.model_validate(user) if user else None


    def reset_password(self, user_id: UUID, new_password: str) -> None:
        """Сбросить пароль пользователя."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Пользователь не найден")
        if len(new_password) < 6:
            raise ValidationError("Пароль должен быть не менее 6 символов")
        user.password_hash = hash_password(new_password)
        self.user_repo.update(user)
        
    def update_profile(self, user_id: UUID, full_name: str | None = None, phone: str | None = None) -> UserDTO:
        """Обновить профиль пользователя."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        if full_name:
            user.full_name = full_name
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
        """Удалить аккаунт."""
        if confirmation != "DELETE":
            raise ValidationError("Для подтверждения введите DELETE")
        self.user_repo.delete(user_id)