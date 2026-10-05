"""Тесты FeedbackService — письмо в поддержку."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.core.config import settings
from app.services.dto.feedback_dto import FeedbackCreateDTO
from app.services.feedback_service import FeedbackService


def test_create_feedback_notifies_support(monkeypatch):
    monkeypatch.setattr(settings, "SUPPORT_EMAIL", "ops@example.com")
    repo = MagicMock()
    created_id = uuid4()
    account_id = uuid4()
    user_id = uuid4()

    def _create(entity):
        entity.id = created_id
        return entity

    repo.create.side_effect = _create
    email = MagicMock()
    service = FeedbackService(repo, email)
    result = service.create_feedback(
        account_id,
        user_id,
        FeedbackCreateDTO(category="bug", message="Что-то сломалось здесь"),
    )
    assert result.id == str(created_id)
    email.send.assert_called_once()
    kwargs = email.send.call_args.kwargs
    assert kwargs["to"] == "ops@example.com"
    assert "bug" in kwargs["subject"]
    assert "Что-то сломалось" in kwargs["body_text"]
