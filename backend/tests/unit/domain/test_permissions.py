"""Unit-тесты матрицы прав."""

from app.domain.permissions import Permission, Role, has_permission


class TestPermissions:
    def test_owner_has_all(self):
        for perm in Permission:
            assert has_permission(Role.OWNER, perm)

    def test_manager_cannot_manage_team(self):
        assert not has_permission(Role.MANAGER, Permission.MANAGE_TEAM)
        assert not has_permission(Role.MANAGER, Permission.MANAGE_ACCOUNT)
        assert has_permission(Role.MANAGER, Permission.WRITE_PROPERTIES)
        assert has_permission(Role.MANAGER, Permission.WRITE_PAYMENTS)

    def test_accountant_finance_only(self):
        assert has_permission(Role.ACCOUNTANT, Permission.WRITE_PAYMENTS)
        assert has_permission(Role.ACCOUNTANT, Permission.WRITE_EXPENSES)
        assert has_permission(Role.ACCOUNTANT, Permission.WRITE_CHARGES)
        assert not has_permission(Role.ACCOUNTANT, Permission.WRITE_PROPERTIES)
        assert not has_permission(Role.ACCOUNTANT, Permission.WRITE_CONTRACTS)
        assert not has_permission(Role.ACCOUNTANT, Permission.MANAGE_TEAM)

    def test_string_role(self):
        assert has_permission("owner", Permission.MANAGE_TEAM)
        assert not has_permission("accountant", Permission.WRITE_TENANTS)
