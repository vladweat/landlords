from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.config import Settings, _validate_production_settings
from app import demo_seed


def test_ensure_user_passes_session_to_user_service(monkeypatch):
    session = object()
    user_id = uuid4()
    account_id = uuid4()
    created_user = SimpleNamespace(id=user_id)
    state = {"user": None}

    class UserRepository:
        def __init__(self, passed_session):
            assert passed_session is session

        def get_by_email(self, email):
            return state["user"]

    class MembershipRepository:
        def __init__(self, passed_session):
            assert passed_session is session

    class UserService:
        def __init__(self, *args, session=None):
            assert session is not None
            assert session is expected_session

        def register(self, dto):
            state["user"] = created_user
            return SimpleNamespace(), SimpleNamespace(id=account_id), "token"

    expected_session = session
    monkeypatch.setattr(demo_seed, "UserRepository", UserRepository)
    monkeypatch.setattr(demo_seed, "MembershipRepository", MembershipRepository)
    monkeypatch.setattr(demo_seed, "AccountRepository", lambda passed: passed)
    monkeypatch.setattr(demo_seed, "AuthSessionRepository", lambda passed: passed)
    monkeypatch.setattr(demo_seed, "AuthSessionService", lambda passed: passed)
    monkeypatch.setattr(demo_seed, "UserService", UserService)

    user, resolved_account_id = demo_seed._ensure_user(
        session,
        email="demo@example.com",
        password="not-a-real-password",
        full_name="Demo",
    )

    assert user is created_user
    assert resolved_account_id == account_id


def test_ensure_existing_user_sets_rls_context_before_membership_lookup(monkeypatch):
    user_id = uuid4()
    account_id = uuid4()
    session = SimpleNamespace(
        execute=lambda statement, params: SimpleNamespace(
            scalar_one_or_none=lambda: account_id
        )
    )
    existing_user = SimpleNamespace(id=user_id)
    membership = SimpleNamespace(account_id=account_id, is_active=True)
    context = {"set": False}

    class UserRepository:
        def __init__(self, passed_session):
            assert passed_session is session

        def get_by_email(self, email):
            return existing_user

    class MembershipRepository:
        def __init__(self, passed_session):
            assert passed_session is session

        def get_by_user_id(self, passed_user_id):
            assert passed_user_id == user_id
            assert context["set"]
            return membership

    monkeypatch.setattr(demo_seed, "UserRepository", UserRepository)
    monkeypatch.setattr(demo_seed, "MembershipRepository", MembershipRepository)
    monkeypatch.setattr(
        demo_seed,
        "set_tenant_context",
        lambda passed_session, passed_account_id: context.update(set=True),
        raising=False,
    )

    user, resolved_account_id = demo_seed._ensure_user(
        session,
        email="demo@example.com",
        password="not-a-real-password",
        full_name="Demo",
    )

    assert user is existing_user
    assert resolved_account_id == account_id


@pytest.mark.parametrize(
    ("app_env", "db_name"),
    [
        ("development", "landlords_db"),
        ("staging", "landlords_demo"),
        ("production", "landlords_demo"),
        ("demo", "landlords_db"),
    ],
)
def test_seed_demo_rejects_non_demo_target_before_opening_database(
    monkeypatch, app_env: str, db_name: str
) -> None:
    session_factory = Mock()
    monkeypatch.setattr(
        demo_seed, "settings", SimpleNamespace(APP_ENV=app_env, DB_NAME=db_name), raising=False
    )
    monkeypatch.setattr(demo_seed, "SessionLocal", session_factory)

    result = demo_seed.run_seed_demo()

    assert result == 1
    session_factory.assert_not_called()


def test_seed_demo_accepts_only_explicit_demo_target(monkeypatch) -> None:
    session = Mock()
    session_factory = Mock(return_value=session)
    account_id = uuid4()
    user = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(
        demo_seed,
        "settings",
        SimpleNamespace(APP_ENV="demo", DB_NAME="landlords_demo"),
        raising=False,
    )
    monkeypatch.setattr(demo_seed, "SessionLocal", session_factory)
    monkeypatch.setattr(
        demo_seed, "_ensure_user", lambda *args, **kwargs: (user, account_id)
    )
    monkeypatch.setattr(demo_seed, "seed_showcase_data", lambda *args, **kwargs: True)

    result = demo_seed.run_seed_demo()

    assert result == 0
    session_factory.assert_called_once_with()
    session.commit.assert_called_once_with()
    session.close.assert_called_once_with()


def test_demo_settings_reject_a_non_demo_database() -> None:
    config = Settings(APP_ENV="demo", DB_NAME="landlords_db")

    with pytest.raises(RuntimeError, match="DB_NAME=landlords_demo"):
        _validate_production_settings(config)


def test_demo_settings_accept_the_dedicated_database() -> None:
    config = Settings(APP_ENV="demo", DB_NAME="landlords_demo")

    _validate_production_settings(config)
