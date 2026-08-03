import sys
import os
from datetime import date, datetime
from unittest.mock import MagicMock, patch, call

import pytest

# backend/ と backend/core/ をパスに追加
_backend = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_core = os.path.join(_backend, "core")
for _p in (_backend, _core):
  if _p not in sys.path:
    sys.path.insert(0, _p)

from core.pipeline import MailPipeline
from core.llm_schemas import Mail, MailAIAnalysis, AnalyzedMail, TodoCreate
from core.enums import TagType, TodoStatus


# ---------------------------------------------------------------------------
# テスト用ヘルパー
# ---------------------------------------------------------------------------

def _make_mail(**kwargs) -> Mail:
    defaults = dict(
        id="test-mail-id",
        from_name="山田 太郎",
        from_email="yamada@example.com",
        to_name="自分",
        to_email="me@example.com",
        title="テストメール",
        body="これはテストです。",
        has_attachments=False,
        day=date(2026, 5, 1),
    )
    defaults.update(kwargs)
    return Mail(**defaults)


def _make_analysis(mail_id: str = "test-mail-id", should_create_todo: bool = False) -> MailAIAnalysis:
    return MailAIAnalysis(
        mail_id=mail_id,
        tag=TagType.business,
        summary="業務メールの要約",
        reason="業務連絡です",
        needs_immediate_reply=False,
        extracted_deadline=None,
        ai_response_message="承知いたしました。",
        model_name="test-model",
        analyzed_at=datetime(2026, 5, 1, 12, 0, 0),
        should_create_todo=should_create_todo,
    )


def _make_analyzed(should_create_todo: bool = False) -> AnalyzedMail:
    mail = _make_mail()
    return AnalyzedMail(
        mail=mail,
        mail_ai_analysis=_make_analysis(mail.id, should_create_todo=should_create_todo),
    )


def _make_todo(user_id: str = "user-1") -> TodoCreate:
    return TodoCreate(
        title="タスク",
        body="内容",
        created_at=datetime(2026, 5, 1, 12, 0, 0),
        user_id=user_id,
        status=TodoStatus.NOT_STARTED,
    )


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

PATCH_BASE = "core.pipeline"

@pytest.fixture
def mocks():
    """外部依存をすべてモック化して MailPipeline インスタンスを返す。"""
    with (
        patch(f"{PATCH_BASE}.GoogleMailClient") as mock_gmc,
        patch(f"{PATCH_BASE}.MailRepository") as mock_repo_cls,
        patch(f"{PATCH_BASE}.GmailParser") as mock_parser_cls,
        patch(f"{PATCH_BASE}.Pretreatment") as mock_pre_cls,
        patch(f"{PATCH_BASE}.MailClassifier") as mock_clf_cls,
        patch(f"{PATCH_BASE}.TodoService") as mock_todo_cls,
    ):
        pipeline = MailPipeline(user_id="user-1", refresh_token="refresh-token", max_results=10)
        yield {
            "pipeline": pipeline,
            "mail_repo": mock_repo_cls.return_value,
            "parser": mock_parser_cls.return_value,
            "pretreatment": mock_pre_cls.return_value,
            "classifier": mock_clf_cls.return_value,
            "todo_generator": mock_todo_cls.return_value,
        }


# ---------------------------------------------------------------------------
# __init__ のテスト
# ---------------------------------------------------------------------------

class TestMailPipelineInit:
    def test_user_id_and_max_results_are_set(self):
        with (
            patch(f"{PATCH_BASE}.GoogleMailClient"),
            patch(f"{PATCH_BASE}.MailRepository"),
            patch(f"{PATCH_BASE}.GmailParser"),
            patch(f"{PATCH_BASE}.Pretreatment"),
            patch(f"{PATCH_BASE}.MailClassifier"),
            patch(f"{PATCH_BASE}.TodoService"),
        ):
            p = MailPipeline(user_id="abc-123", refresh_token="refresh-token", max_results=5)
            assert p._user_id == "abc-123"
            assert p._max_results == 5

    def test_default_max_results_is_3(self):
        with (
            patch(f"{PATCH_BASE}.GoogleMailClient"),
            patch(f"{PATCH_BASE}.MailRepository"),
            patch(f"{PATCH_BASE}.GmailParser"),
            patch(f"{PATCH_BASE}.Pretreatment"),
            patch(f"{PATCH_BASE}.MailClassifier"),
            patch(f"{PATCH_BASE}.TodoService"),
        ):
            p = MailPipeline(user_id="x", refresh_token="refresh-token")
            assert p._max_results == 3


# ---------------------------------------------------------------------------
# run() のテスト
# ---------------------------------------------------------------------------

class TestRun:
    def test_returns_number_of_processed_mails(self, mocks):
        pipeline = mocks["pipeline"]
        mocks["mail_repo"].fetch_id_list.return_value = ["id1", "id2", "id3"]
        pipeline._process_one = MagicMock()

        with patch(f"{PATCH_BASE}.SessionLocal", return_value=MagicMock()):
            processed, errors = pipeline.run()

        assert processed == 3
        assert errors == []

    def test_calls_process_one_for_each_message_id(self, mocks):
        pipeline = mocks["pipeline"]
        mocks["mail_repo"].fetch_id_list.return_value = ["id1", "id2"]
        pipeline._process_one = MagicMock()

        mock_db = MagicMock()
        with patch(f"{PATCH_BASE}.SessionLocal", return_value=mock_db):
            pipeline.run()

        pipeline._process_one.assert_has_calls(
            [call(mock_db, "id1"), call(mock_db, "id2")]
        )

    def test_passes_max_results_to_fetch_id_list(self, mocks):
        pipeline = mocks["pipeline"]
        mocks["mail_repo"].fetch_id_list.return_value = []
        pipeline._process_one = MagicMock()

        with patch(f"{PATCH_BASE}.SessionLocal", return_value=MagicMock()):
            pipeline.run()

        mocks["mail_repo"].fetch_id_list.assert_called_once_with(max_results=10, after_date=None)

    def test_returns_zero_when_no_mails(self, mocks):
        pipeline = mocks["pipeline"]
        mocks["mail_repo"].fetch_id_list.return_value = []
        pipeline._process_one = MagicMock()

        with patch(f"{PATCH_BASE}.SessionLocal", return_value=MagicMock()):
            processed, errors = pipeline.run()

        assert processed == 0
        assert errors == []
        pipeline._process_one.assert_not_called()

    def test_closes_db_session_on_success(self, mocks):
        pipeline = mocks["pipeline"]
        mocks["mail_repo"].fetch_id_list.return_value = []
        pipeline._process_one = MagicMock()

        mock_db = MagicMock()
        with patch(f"{PATCH_BASE}.SessionLocal", return_value=mock_db):
            pipeline.run()

        mock_db.close.assert_called_once()

    def test_records_error_and_continues_when_process_one_raises(self, mocks):
        """_process_one が例外を出しても run() は落ちず、エラーとして記録して続行する。"""
        pipeline = mocks["pipeline"]
        mocks["mail_repo"].fetch_id_list.return_value = ["id1"]
        pipeline._process_one = MagicMock(side_effect=RuntimeError("AI失敗"))

        mock_db = MagicMock()
        with patch(f"{PATCH_BASE}.SessionLocal", return_value=mock_db):
            processed, errors = pipeline.run()

        assert processed == 0
        assert len(errors) == 1
        assert "AI失敗" in errors[0]
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()


# ---------------------------------------------------------------------------
# _process_one() のテスト
# ---------------------------------------------------------------------------

class TestProcessOne:

    def _setup_mocks(self, mocks, mail=None, pretreatment_result="前処理済み本文", analyzed=None):
        """_process_one テスト用の共通モック設定。"""
        if mail is None:
            mail = _make_mail()
        if analyzed is None:
            analyzed = _make_analyzed()
        mocks["mail_repo"].fetch.return_value = {"payload": {}}
        mocks["parser"].parse.return_value = mail
        mocks["pretreatment"].process.return_value = pretreatment_result
        mocks["classifier"].classify.return_value = analyzed
        return mail, analyzed

    def test_fetches_raw_mail_with_message_id(self, mocks):
        pipeline = mocks["pipeline"]
        self._setup_mocks(mocks)

        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment"),
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=False, assessment=None)
            pipeline._process_one(MagicMock(), "msg-xyz")

        mocks["mail_repo"].fetch.assert_called_once_with("msg-xyz")

    def test_parses_fetched_raw_mail(self, mocks):
        pipeline = mocks["pipeline"]
        raw = {"payload": {"mimeType": "text/plain"}}
        mocks["mail_repo"].fetch.return_value = raw
        mocks["parser"].parse.return_value = _make_mail()
        mocks["pretreatment"].process.return_value = "本文"
        mocks["classifier"].classify.return_value = _make_analyzed()

        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment"),
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=False, assessment=None)
            pipeline._process_one(MagicMock(), "msg-1")

        mocks["parser"].parse.assert_called_once_with(raw)

    def test_calls_pretreatment_with_parsed_body(self, mocks):
        pipeline = mocks["pipeline"]
        mail = _make_mail(body="元の本文")
        self._setup_mocks(mocks, mail=mail)

        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment"),
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=False, assessment=None)
            pipeline._process_one(MagicMock(), "msg-1")

        mocks["pretreatment"].process.assert_called_once_with("元の本文")

    def test_skips_when_already_analyzed(self, mocks):
        """DBで既に分析済み(is_analyzed)のメールは再分析しない。"""
        self._setup_mocks(mocks)

        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment"),
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=True, assessment=None)
            pipeline = mocks["pipeline"]
            pipeline._process_one(MagicMock(), "msg-1")

        mocks["classifier"].classify.assert_not_called()

    def test_skips_when_body_is_empty(self, mocks):
        """前処理後の本文が空(空白のみ含む)ならAI分析をスキップする。"""
        pipeline = mocks["pipeline"]
        self._setup_mocks(mocks, pretreatment_result="   ")

        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment"),
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=False, assessment=None)
            pipeline._process_one(MagicMock(), "msg-1")

        mocks["classifier"].classify.assert_not_called()

    def test_saves_mail_and_assessment_to_db(self, mocks):
        pipeline = mocks["pipeline"]
        analyzed = _make_analyzed(should_create_todo=False)
        mail, analyzed = self._setup_mocks(mocks, analyzed=analyzed)

        mock_db = MagicMock()
        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment") as mock_save_assessment,
            patch(f"{PATCH_BASE}.save_todo"),
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=False, assessment=None)
            pipeline._process_one(mock_db, "msg-1")

        mock_save_mail.assert_called_once_with(mock_db, mail, "user-1")
        mock_save_assessment.assert_called_once_with(
            mock_db, mail.id, analyzed.mail_ai_analysis
        )

    def test_creates_todo_when_should_create_todo_is_true(self, mocks):
        pipeline = mocks["pipeline"]
        analyzed = _make_analyzed(should_create_todo=True)
        todo = _make_todo()
        mail, analyzed = self._setup_mocks(mocks, analyzed=analyzed)
        mocks["todo_generator"].create.return_value = todo

        mock_db = MagicMock()
        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment"),
            patch(f"{PATCH_BASE}.save_todo") as mock_save_todo,
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=False, assessment=None)
            pipeline._process_one(mock_db, "msg-1")

        mocks["todo_generator"].create.assert_called_once_with(
            analyzed_mail=analyzed, user_id="user-1"
        )
        mock_save_todo.assert_called_once_with(
            mock_db, "user-1", todo, analyzed.mail_ai_analysis.extracted_deadline
        )

    def test_skips_todo_when_should_create_todo_is_false(self, mocks):
        pipeline = mocks["pipeline"]
        analyzed = _make_analyzed(should_create_todo=False)
        self._setup_mocks(mocks, analyzed=analyzed)

        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment"),
            patch(f"{PATCH_BASE}.save_todo") as mock_save_todo,
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=False, assessment=None)
            pipeline._process_one(MagicMock(), "msg-1")

        mocks["todo_generator"].create.assert_not_called()
        mock_save_todo.assert_not_called()

    def test_classify_is_called_after_pretreatment(self, mocks):
        """前処理後の本文でAI分類が呼ばれることを確認する。"""
        pipeline = mocks["pipeline"]
        mail = _make_mail(body="元の本文")
        analyzed = _make_analyzed()
        mocks["mail_repo"].fetch.return_value = {"payload": {}}
        mocks["parser"].parse.return_value = mail
        mocks["pretreatment"].process.return_value = "前処理済み"
        mocks["classifier"].classify.return_value = analyzed

        with (
            patch(f"{PATCH_BASE}.save_mail") as mock_save_mail,
            patch(f"{PATCH_BASE}.save_mail_assessment"),
        ):
            mock_save_mail.return_value = MagicMock(is_analyzed=False, assessment=None)
            pipeline._process_one(MagicMock(), "msg-1")

        classified_mail = mocks["classifier"].classify.call_args[0][0]
        assert classified_mail.body == "前処理済み"
