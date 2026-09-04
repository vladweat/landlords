"""Роли и права доступа для мультипользовательского аккаунта."""

from enum import StrEnum


class Role(StrEnum):
    """Роль участника аккаунта."""

    OWNER = "owner"
    MANAGER = "manager"
    ACCOUNTANT = "accountant"


class Permission(StrEnum):
    """Право на действие в рамках аккаунта."""

    MANAGE_TEAM = "manage_team"
    MANAGE_ACCOUNT = "manage_account"
    WRITE_PROPERTIES = "write_properties"
    WRITE_TENANTS = "write_tenants"
    WRITE_CONTRACTS = "write_contracts"
    WRITE_DOCUMENTS = "write_documents"
    WRITE_PAYMENTS = "write_payments"
    WRITE_CHARGES = "write_charges"
    WRITE_EXPENSES = "write_expenses"
    WRITE_REMINDERS = "write_reminders"


_ALL_PERMISSIONS = frozenset(Permission)

_MANAGER_PERMISSIONS = frozenset(
    {
        Permission.WRITE_PROPERTIES,
        Permission.WRITE_TENANTS,
        Permission.WRITE_CONTRACTS,
        Permission.WRITE_DOCUMENTS,
        Permission.WRITE_PAYMENTS,
        Permission.WRITE_CHARGES,
        Permission.WRITE_EXPENSES,
        Permission.WRITE_REMINDERS,
    }
)

_ACCOUNTANT_PERMISSIONS = frozenset(
    {
        Permission.WRITE_PAYMENTS,
        Permission.WRITE_CHARGES,
        Permission.WRITE_EXPENSES,
        Permission.WRITE_REMINDERS,
    }
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: _ALL_PERMISSIONS,
    Role.MANAGER: _MANAGER_PERMISSIONS,
    Role.ACCOUNTANT: _ACCOUNTANT_PERMISSIONS,
}

# Роли, которые можно назначить участнику при создании/смене
ASSIGNABLE_ROLES = frozenset({Role.MANAGER, Role.ACCOUNTANT})


def has_permission(role: Role | str, permission: Permission) -> bool:
    """Проверить, есть ли у роли указанное право."""
    role_enum = Role(role) if not isinstance(role, Role) else role
    return permission in ROLE_PERMISSIONS.get(role_enum, frozenset())
