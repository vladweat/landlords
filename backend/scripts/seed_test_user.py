"""Обёртка: демо-данные для существующего пользователя test@test.com.

Предпочтительно: python -m app.cli seed-demo
"""

from __future__ import annotations

from app.db.repositories.membership_repo import MembershipRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import SessionLocal
from app.demo_seed import seed_showcase_data

EMAIL = "test@test.com"


def main() -> int:
    session = SessionLocal()
    try:
        user = UserRepository(session).get_by_email(EMAIL)
        if not user:
            print(f"error: user {EMAIL} not found")
            return 1

        membership = MembershipRepository(session).get_by_user_id(user.id)
        if not membership or not membership.is_active:
            print("error: no active membership")
            return 1

        print(f"user_id={user.id}")
        print(f"account_id={membership.account_id}")

        applied = seed_showcase_data(
            session, user_id=user.id, account_id=membership.account_id
        )
        session.commit()
        if applied:
            print("ok: demo seed committed")
        else:
            print("seed already applied — nothing to do")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"error: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
