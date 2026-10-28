from unittest.mock import Mock
from uuid import uuid4

from app.db.tenant_context import set_tenant_context


def test_set_tenant_context_uses_transaction_local_setting() -> None:
    session = Mock()
    account_id = uuid4()

    set_tenant_context(session, account_id)

    session.execute.assert_called_once()
    statement, parameters = session.execute.call_args.args
    assert "set_config" in str(statement)
    assert "true" in str(statement).lower()
    assert parameters == {"account_id": str(account_id)}
    session.commit.assert_not_called()


def test_set_tenant_context_can_be_replaced_for_a_later_transaction() -> None:
    session = Mock()
    first_account_id = uuid4()
    second_account_id = uuid4()

    set_tenant_context(session, first_account_id)
    set_tenant_context(session, second_account_id)

    assert [call.args[1] for call in session.execute.call_args_list] == [
        {"account_id": str(first_account_id)},
        {"account_id": str(second_account_id)},
    ]
    session.commit.assert_not_called()
