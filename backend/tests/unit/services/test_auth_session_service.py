"""Unit-тесты жизненного цикла авторизационных сессий."""

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.services.auth_session_service import AuthSessionService


def test_issue_access_token_persists_session_and_embeds_its_id():
    repository = Mock()
    service = AuthSessionService(repository)
    user_id = uuid4()
    account_id = uuid4()

    token = service.issue_access_token(user_id, account_id)
    session = repository.create.call_args.args[0]
    claims = decode_access_token(token)

    assert session.user_id == user_id
    assert session.account_id == account_id
    assert session.expires_at > datetime.now(timezone.utc)
    assert claims["jti"] == str(session.id)
    assert UUID(claims["sub"]) == user_id
    assert UUID(claims["account_id"]) == account_id
    repository.delete_expired.assert_called_once()


def test_require_active_rejects_revoked_or_unknown_session():
    repository = Mock()
    repository.is_active.return_value = False
    service = AuthSessionService(repository)

    with pytest.raises(UnauthorizedError, match="Session is revoked or expired"):
        service.require_active(uuid4(), uuid4(), uuid4())


def test_revoke_access_token_marks_its_session_revoked():
    repository = Mock()
    service = AuthSessionService(repository)
    token = service.issue_access_token(uuid4(), uuid4())
    session_id = UUID(decode_access_token(token)["jti"])

    service.revoke_access_token(token)

    repository.revoke.assert_called_once()
    assert repository.revoke.call_args.args[0] == session_id


def test_revoke_all_for_user_marks_all_sessions_revoked():
    repository = Mock()
    service = AuthSessionService(repository)
    user_id = uuid4()

    service.revoke_all_for_user(user_id)

    repository.revoke_all_for_user.assert_called_once()
    assert repository.revoke_all_for_user.call_args.args[0] == user_id
