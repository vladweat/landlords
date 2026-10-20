"""CLI для локальной разработки и bootstrap.

Примеры:
  python -m app.cli create-user --email admin@example.com --password secret123 --full-name Admin
  python -m app.cli seed --email admin@example.com --password secret123
  python -m app.cli seed-demo
"""

import argparse
import sys
from uuid import UUID

from app.core.exceptions import ConflictError
from app.db.repositories.account_repo import AccountRepository
from app.db.repositories.auth_session_repo import AuthSessionRepository
from app.db.repositories.membership_repo import MembershipRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import SessionLocal
from app.demo_seed import (
    DEFAULT_DEMO_EMAIL,
    DEFAULT_DEMO_FULL_NAME,
    DEFAULT_DEMO_PASSWORD,
    run_seed_demo,
)
from app.services.dto.property_dto import PropertyCreateDTO
from app.services.dto.tenant_dto import TenantCreateDTO
from app.services.dto.user_dto import UserCreateDTO
from app.services.auth_session_service import AuthSessionService
from app.services.property_service import PropertyService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService


def _build_user_service(session) -> UserService:
    return UserService(
        UserRepository(session),
        AccountRepository(session),
        MembershipRepository(session),
        AuthSessionService(AuthSessionRepository(session)),
    )


def cmd_create_user(args: argparse.Namespace) -> int:
    """Создать пользователя и аккаунт (тот же flow, что register)."""
    session = SessionLocal()
    try:
        service = _build_user_service(session)
        user, account, _token = service.register(
            UserCreateDTO(
                email=args.email,
                password=args.password,
                full_name=args.full_name,
            )
        )
        session.commit()
        print(f"user_id={user.id}")
        print(f"account_id={account.id}")
        print(f"email={user.email}")
        return 0
    except ConflictError as exc:
        session.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        session.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


def cmd_seed(args: argparse.Namespace) -> int:
    """Создать пользователя + демо property и tenant."""
    session = SessionLocal()
    try:
        user_service = _build_user_service(session)
        user, account, _token = user_service.register(
            UserCreateDTO(
                email=args.email,
                password=args.password,
                full_name=args.full_name,
            )
        )
        account_id: UUID = account.id

        property_service = PropertyService(PropertyRepository(session))
        prop = property_service.create_property(
            account_id,
            PropertyCreateDTO(
                city="Москва",
                street="Тверская",
                house="1",
                type="apartment",
                size_m2=45.0,
            ),
        )

        tenant_service = TenantService(TenantRepository(session))
        tenant = tenant_service.create_tenant(
            account_id,
            TenantCreateDTO(
                full_name="Иван Демо",
                email="tenant@example.com",
                phone="+79001234567",
            ),
        )

        session.commit()
        print(f"user_id={user.id}")
        print(f"account_id={account_id}")
        print(f"property_id={prop.id}")
        print(f"tenant_id={tenant.id}")
        return 0
    except ConflictError as exc:
        session.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        session.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


def cmd_seed_demo(args: argparse.Namespace) -> int:
    """Создать showcase-демо: пользователь + объекты, договоры, платежи, расходы."""
    return run_seed_demo(
        email=args.email,
        password=args.password,
        full_name=args.full_name,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="Landlords backend CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    create_user = sub.add_parser("create-user", help="Создать пользователя и аккаунт")
    create_user.add_argument("--email", required=True)
    create_user.add_argument("--password", required=True)
    create_user.add_argument("--full-name", default="Admin")
    create_user.set_defaults(func=cmd_create_user)

    seed = sub.add_parser("seed", help="Создать пользователя + demo property/tenant")
    seed.add_argument("--email", required=True)
    seed.add_argument("--password", required=True)
    seed.add_argument("--full-name", default="Admin")
    seed.set_defaults(func=cmd_seed)

    seed_demo = sub.add_parser(
        "seed-demo",
        help="Showcase-демо для портфолио (объекты, договоры, платежи, расходы)",
    )
    seed_demo.add_argument("--email", default=DEFAULT_DEMO_EMAIL)
    seed_demo.add_argument("--password", default=DEFAULT_DEMO_PASSWORD)
    seed_demo.add_argument("--full-name", default=DEFAULT_DEMO_FULL_NAME)
    seed_demo.set_defaults(func=cmd_seed_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
