import pytest
from unittest.mock import MagicMock

from core.todo_service import TodoService


# ダミークラス
class DummyMail:
    def __init__(self, title: str, body: str):
        self.title = title
        self.body = body


class DummyAnalyzedMail:
    def __init__(self, title: str, body: str):
        self.mail = DummyMail(title, body)


class DummyTodoCreate:
    def __init__(self, title: str, body: str, user_id: str):
        self.title = title
        self.body = body
        self.user_id = user_id


def test_create_success():
    # Arrange
    service = TodoService()

    analyzed_mail = DummyAnalyzedMail(
        title="買い物",
        body="牛乳と卵を買う"
    )
    user_id = "user-123"

    expected = DummyTodoCreate(
        title="買い物",
        body="牛乳と卵を買う",
        user_id=user_id
    )

    # _chain.invoke をモック
    service._chain = MagicMock()
    service._chain.invoke.return_value = expected

    # Act
    result = service.create(analyzed_mail, user_id)

    # Assert
    assert result == expected

    service._chain.invoke.assert_called_once_with({
        "title": "買い物",
        "body": "牛乳と卵を買う",
        "user_id": user_id,
    })